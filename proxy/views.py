from decimal import Decimal, ROUND_HALF_UP
import requests
import struct
import xml.etree.ElementTree as ETree

from django.http import HttpResponseBadRequest, HttpResponse

from proxy.models import Chunk


def get_chunk(request):
    BOUNDINGBOX_EXTRA = Decimal('0.008')

    lat = int(request.GET.get('lat'))
    lon = int(request.GET.get('lon'))

    def lat_to_int(lat):
        lat = int((Decimal(lat) * 10000000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        return min(900000000, max(-900000000, lat))

    def lon_to_int(lon):
        lon = int((Decimal(lon) * 10000000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        return (lon + 1800000000) % 3600000000 - 1800000000

    def get_str_id(strcache, str):
        try:
            return strcache.index(str)
        except ValueError:
            strcache.append(str)
            return len(strcache) - 1

    if lat is None or lon is None:
        return HttpResponseBadRequest('Missing GET argument "lat" or "lon"!')

    # Validate and clean latitude and longitude. Latitude
    # must be [-90 – 90) and longitude [-180 – 180).
    if lat < -9000 or lat >= 9000:
        return HttpResponseBadRequest('Invalid latitude!')
    lon = (lon + 18000) % 36000 - 18000
    lat_d = Decimal(lat) / Decimal(100)
    lon_d = Decimal(lon) / Decimal(100)

    chunk = Chunk.objects.filter(lat=lat, lon=lon).first()
    if chunk:
        return HttpResponse(chunk.data, content_type='application/octet-stream')

    # Chunk does not exist, so it must be loaded
    bb_lat_min = lat_d - BOUNDINGBOX_EXTRA
    bb_lat_max = lat_d + Decimal('0.01') + BOUNDINGBOX_EXTRA
    bb_lon_min = lon_d - BOUNDINGBOX_EXTRA
    bb_lon_max = lon_d + Decimal('0.01') + BOUNDINGBOX_EXTRA

    # Fetch nodes
    query = """
        <query type="node">
            <bbox-query s="{bb_lat_min}" n="{bb_lat_max}" w="{bb_lon_min}" e="{bb_lon_max}"/>
        </query>
        <print/>
    """.format(
        bb_lat_min=bb_lat_min,
        bb_lat_max=bb_lat_max,
        bb_lon_min=bb_lon_min,
        bb_lon_max=bb_lon_max,
    )
    response = requests.post('http://overpass-api.de/api/interpreter', data=query)
    nodes_xml = ETree.fromstring(response.text)

    # Fetch ways
    query = """
        <query type="way">
            <bbox-query s="{bb_lat_min}" n="{bb_lat_max}" w="{bb_lon_min}" e="{bb_lon_max}"/>
        </query>
        <print/>
    """.format(
        bb_lat_min=bb_lat_min,
        bb_lat_max=bb_lat_max,
        bb_lon_min=bb_lon_min,
        bb_lon_max=bb_lon_max,
    )
    response = requests.post('http://overpass-api.de/api/interpreter', data=query)
    ways_xml = ETree.fromstring(response.text)

    # Prepare string cache. This is used to reduce space
    # waste of strings that occur multiple times.
    strcache = []

    # Convert nodes to bytes
    nodes_bytes = b''
    nodes_xml = list(nodes_xml.findall('node'))
    nodes_bytes += struct.pack('>I', len(nodes_xml))
    for node_xml in nodes_xml:
        # ID
        nodes_bytes += struct.pack('>Q', int(node_xml.get('id')))
        # Latitude and longitude
        nodes_bytes += struct.pack('>ii', lat_to_int(node_xml.get('lat')), lon_to_int(node_xml.get('lon')))
        # Tags
        tags_xml = list(node_xml.findall('tag'))
        nodes_bytes += struct.pack('>H', len(tags_xml))
        for tag_xml in tags_xml:
            key = get_str_id(strcache, tag_xml.get('k'))
            value = get_str_id(strcache, tag_xml.get('v'))
            nodes_bytes += struct.pack('>HH', key, value)

    # Convert ways to bytes
    ways_bytes = b''
    ways_xml = list(ways_xml.findall('way'))
    ways_bytes += struct.pack('>I', len(ways_xml))
    for way_xml in ways_xml:
        # ID
        ways_bytes += struct.pack('>Q', int(way_xml.get('id')))
        # Nodes
        way_nodes_xml = way_xml.findall('nd')
        ways_bytes += struct.pack('>H', len(way_nodes_xml))
        for way_node_xml in way_nodes_xml:
            ways_bytes += struct.pack('>Q', int(way_node_xml.get('ref')))
        # Tags
        tags_xml = list(way_xml.findall('tag'))
        ways_bytes += struct.pack('>H', len(tags_xml))
        for tag_xml in tags_xml:
            key = get_str_id(strcache, tag_xml.get('k'))
            value = get_str_id(strcache, tag_xml.get('v'))
            ways_bytes += struct.pack('>HH', key, value)

    # Form the final bytes
    data = b''
    # Version
    data += struct.pack('>H', 0)
    # String cache
    data += struct.pack('>H', len(strcache))
    for s in strcache:
        s = s.encode('utf8')
        data += struct.pack('>H', len(s))
        data += s
    # Nodes and ways
    data += nodes_bytes
    data += ways_bytes

    Chunk.objects.create(
        lat=lat,
        lon=lon,
        data=data
    )

    return HttpResponse(data, content_type='application/octet-stream')

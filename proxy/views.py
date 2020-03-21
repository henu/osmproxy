from decimal import Decimal
import importlib
import struct
import xml.etree.ElementTree as ETree

import requests

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponse

from proxy.models import Chunk
from proxy.utils import lat_to_int, lon_to_int, bytes_to_rich_data


def get_chunk(request):

    def get_str_id(strcache, s):
        try:
            return strcache.index(s)
        except ValueError:
            strcache.append(s)
            return len(strcache) - 1

    BOUNDINGBOX_EXTRA = Decimal('0.008')

    func_path = getattr(settings, 'CUSTOM_CHUNK_SERIALIZATION_FUNCTION', None)

    lat = int(request.GET.get('lat'))
    lon = int(request.GET.get('lon'))

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
        # If custom data should be returned instead
        if func_path:
            return HttpResponse(chunk.custom_data, content_type='application/octet-stream')
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

    # If custom data should be built
    custom_data = None
    if func_path:
        mod_name, func_name = func_path.rsplit('.', 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        custom_data = func(bytes_to_rich_data(data))

    Chunk.objects.create(
        lat=lat,
        lon=lon,
        data=data,
        custom_data=custom_data,
    )

    if func_path:
        return HttpResponse(custom_data, content_type='application/octet-stream')
    return HttpResponse(data, content_type='application/octet-stream')

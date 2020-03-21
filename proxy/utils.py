from decimal import Decimal, ROUND_HALF_UP
import struct


def lat_to_int(lat):
    """ Convert decimal format latitude to int32 format.
    """
    lat = int((Decimal(lat) * 10000000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return min(900000000, max(-900000000, lat))


def lon_to_int(lon):
    """ Convert decimal format longitude to int32 format.
    """
    lon = int((Decimal(lon) * 10000000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return (lon + 1800000000) % 3600000000 - 1800000000


def bytes_to_rich_data(data):
    ofs = 0

    # Version
    version = struct.unpack('>H', data[ofs:ofs+2])[0]
    ofs += 2
    if version != 0:
        raise Exception('Unsupported version!')

    # String cache
    strcache = []
    strcache_size = struct.unpack('>H', data[ofs:ofs+2])[0]
    ofs += 2
    for _i in range(strcache_size):
        str_size = struct.unpack('>H', data[ofs:ofs+2])[0]
        ofs += 2
        s = data[ofs:ofs+str_size].decode('utf8')
        ofs += str_size
        strcache.append(s)

    # Nodes
    nodes = {}
    nodes_size = struct.unpack('>I', data[ofs:ofs+4])[0]
    ofs += 4
    for _i in range(nodes_size):
        # ID
        node_id = struct.unpack('>Q', data[ofs:ofs+8])[0]
        ofs += 8
        # Latitude and longitude
        lat, lon = struct.unpack('>ii', data[ofs:ofs+8])
        ofs += 8
        # Tags
        tags = {}
        tags_size = struct.unpack('>H', data[ofs:ofs+2])[0]
        ofs += 2
        for _j in range(tags_size):
            key_i, value_i = struct.unpack('>HH', data[ofs:ofs+4])
            ofs += 4
            key = strcache[key_i]
            value = strcache[value_i]
            tags[key] = value
        # Store
        nodes[node_id] = {
            'lat': lat,
            'lon': lon,
            'tags': tags,
        }

    # Ways
    ways = {}
    ways_size = struct.unpack('>I', data[ofs:ofs+4])[0]
    ofs += 4
    for _i in range(ways_size):
        # ID
        way_id = struct.unpack('>Q', data[ofs:ofs+8])[0]
        ofs += 8
        # Nodes
        way_nodes = []
        way_nodes_size = struct.unpack('>H', data[ofs:ofs+2])[0]
        ofs += 2
        for _j in range(way_nodes_size):
            way_nodes.append(struct.unpack('>Q', data[ofs:ofs+8])[0])
            ofs += 8
        # Tags
        tags = {}
        tags_size = struct.unpack('>H', data[ofs:ofs+2])[0]
        ofs += 2
        for _j in range(tags_size):
            key_i, value_i = struct.unpack('>HH', data[ofs:ofs+4])
            ofs += 4
            key = strcache[key_i]
            value = strcache[value_i]
            tags[key] = value
        # Store
        ways[way_id] = {
            'nodes': way_nodes,
            'tags': tags,
        }

    return {
        'nodes': nodes,
        'ways': ways,
    }

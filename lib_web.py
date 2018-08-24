""" PTC-Sim's web library.
"""

from datetime import datetime

from flask_googlemaps import Map

from lib_app import bos_log

# HTML constants
TABLE_TAG = '<table border="1px" style="font-size: 12px;" class="table-condensed compact nowrap table table-striped table-bordered HTMLTable no-footer" width="100%" cellspacing="0">'
WEBTIME_FORMAT = "%Y-%m-%d %H:%M:%S"

MAP_LOCO_GRN = '/static/img/loco_ico_grn_sm.png'
MAP_LOCO_RED = '/static/img/loco_ico_red_sm.png'
MAP_LOCO_GRN_SEL = '/static/img/loco_ico_grn_sm.png'
MAP_LOCO_RED_SEL = '/static/img/loco_ico_red_sm.png'
MAP_BASE_GRN = '/static/img/base_ico_grn.png'
MAP_BASE_RED = '/static/img/base_ico_red.png'
MAP_BASE_GRN_SEL = '/static/img/base_ico_grn.png'
MAP_BASE_RED_SEL = '/static/img/base_ico_red.png'

# HTML Color constants
GRN = ''
RED = ''
YELLOW = '#dfd005'


class WebTable:
    """ An HTML Table, with build methods.
    """
    _default_head_tag = TABLE_TAG
    
    def __init__(self, head_tag=None, col_headers=[]):
        """ num_columns: Number of table columns
            col_headers: A list of strings representing table column headings
        """
        self._head_tag = {None: self._default_head_tag}.get(head_tag, head_tag)
        self._header = ''.join(['<th>' + h + '</th>' for h in col_headers])
        self._footer = '</table>'
        self._rows = []

    def html(self):
        """ Returns an html representation of the table.
        """
        html_table = self._head_tag

        if self._header:
            html_table += '<thead><tr>'
            html_table += self._header
            html_table += '</tr></thead>'
        
        html_table += '<tbody>'
        html_table += ''.join([r for r in self._rows])
        html_table += '</tbody>'
        html_table += self._footer

        return html_table

    def add_row(self, cells, style=None, onclick=None, row_id=None):
        """ Adds a row of the given cells (a list of cells) and html properties.
            Ex usage: add_row([cell('hello'), cell('world')], onclick=DoHello())
        """
        row_str = '<tr'
        
        if row_id:
            row_str += ' id="' + row_id + '"'
        if not style:
            style = ''
        if onclick:
            row_str += ' onclick="' + onclick + '"'
            style = 'cursor:pointer;' + style
        if style:
            row_str += ' style="' + style + '"'

        row_str += '>'
        row_str += ''.join([c for c in cells])
        row_str += '</tr>'
        
        self._rows.append(row_str)


def cell( content, colspan=None, style=None):
    """ Returns the given parameters as a well-formed HTML table cell tag.
        content: (str) The cell's inner content. Ex: Hello World!
        colspan: (int) HTML colspan tag content.
        style  : (str) HTML style tag content.
    """
    cell_str = '<td'

    if colspan:
        cell_str += ' colspan=' + str(colspan)
    if style:
        cell_str += ' style="' + style + '"'

    cell_str += '>' + content + '</td>'
    
    return cell_str


def webtime(datetime_obj):
    """ Given a datetime object, returns a string representation formatted
        according to WEBTIME_FORMAT.
    """
    if type(datetime_obj) is datetime:
        return datetime_obj.strftime(WEBTIME_FORMAT)


def get_locos_table(track):
    """ Given a track object, returns the locos html table for web display.
    """
    # Locos table is an outter table consisting of an inner table for each loco
    outter = WebTable(col_headers=[' ID', ' Status'])

    for loco in sorted(track.locos.values(), key=lambda x: x.ID):
        # Connection interface row values
        conn_values = []
        for c in loco.conns.values():
            if not c.connected_to:
                conn_values.append('N/A')
            else:
                conn_values.append(c.connected_to.ID)

        # Last seen row value
        lastseentime = track.get_lastseen(loco)
        if not lastseentime:
            lastseen = 'N/A'
        else:
            lastseen = str(loco.coords.marker)
            lastseen += ' @ ' + webtime(lastseentime)

        # This inner tables onclick handler function call
        loco_onclick_str = "home_loco_select('" + loco.name + "')"

        # Build inner table
        inner = WebTable(col_headers=[c for c in loco.conns.keys()])
        inner.add_row([cell(c) for c in conn_values])       # Radio status row
        inner.add_row([cell('<b>Last Seen Milepost/Time</b>', colspan=2)])
        inner.add_row([cell(lastseen, colspan=2)])          # Last seen row

        outter.add_row([cell(loco.ID), cell(inner.html())], 
                       onclick=loco_onclick_str,
                       row_id=loco.name)

    return outter.html()


def get_loco_connline(track, loco_id):
    """ Given a track object and locomotive id string, returns a polyline
        between the loco and connected base stations.
    """
    raise NotImplementedError

    
def get_trackline(track):
    """ Returns a polyline representation of the given track, based on its
        mileposts.
    """
    tracklines = []
    for mp in track.mileposts_sorted:
        line = {'lat': mp.lat,
                'lng': mp.long}
        tracklines.append(line)

    polyline = {
        'stroke_color': YELLOW,
        'stroke_opacity': 1.0,
        'stroke_weight': 2,
        'path': list(ln for ln in tracklines)
    }

    return polyline


def get_status_map(track, tracklines, loco=None):
    """ Gets the main status map for the given track.
        If not loco, all locos are added to the map. Else only the loco
        having the given ID is added.
    """
    map_markers = []  # Map markers, for the Google.map.markers property.
    base_points = []  # All base station points, (p1, p2). For map centering.   

    # Append markers to map_markers for --
    # -- Loco(s).
    if not loco:
        locos = track.locos.values()
    else:
        try:
            locos = [loco]  # Put in list form, so we can still iterate
        except KeyError:
            bos_log.error('get_status_map received an invalid loco: ' + loco.ID)
            locos = []

    for l in locos:
        status_tbl = WebTable()
        status_tbl.add_row([cell('Device'), cell(l.name)])
        status_tbl.add_row([cell('Status'), cell('OK')])
        status_tbl.add_row([cell('Location'), cell(str(l.coords))])
        status_tbl.add_row([cell('Last Seen'), cell('NA')])

        marker = {'title': l.name,
                  'icon': MAP_LOCO_GRN,
                  'lat': l.coords.lat,
                  'lng': l.coords.long,
                  'infobox': status_tbl.html()}
        map_markers.append(marker)

    # -- Bases:
    for base in track.bases.values():
        status_tbl = WebTable()
        status_tbl.add_row([cell('Device'), cell(base.name)])
        status_tbl.add_row([cell('Status'), cell('OK')])
        status_tbl.add_row([cell('Location'), cell(str(base.coords))])
        status_tbl.add_row([cell('Last Seen'), cell('NA')])

        marker = {'title': base.name,
                  'icon': MAP_BASE_GRN,
                  'lat': base.coords.lat,
                  'lng': base.coords.long,
                  'infobox': status_tbl.html()}
        map_markers.append(marker)
        base_points.append((base.coords.lat, base.coords.long))

    # Determine where to center map
    if loco:
        # Center map on the loco given by loco_id param, if given.
        center = (loco.coords.lat, loco.coords.long)
    else:
        # Else, center on the centroid of all base station pts.
        x, y = zip(*base_points)
        center = (max(x) + min(x)) / 2.0, (max(y) + min(y)) / 2.0

    panel_map = Map(identifier='panel_map',
                    varname='panel_map',
                    lat=center[0],
                    lng=center[1],
                    maptype='SATELLITE',
                    zoom='6',
                    markers=list(m for m in map_markers),
                    style="height:600px;width:755px;margin:0;",
                    polylines=[tracklines])
    return panel_map

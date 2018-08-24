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

# HTML Class constants

# HTML Color constants
GRN = ''
RED = ''
YELLOW = '#dfd005'


class WebTable:
    """ An HTML Table, with build methods.
    """
    _default_head_tag = TABLE_TAG
    
    def __init__(self, head_tag=None, col_headers=[], onclick=None):
        """ num_columns: Number of table columns
            col_headers: A list of strings representing table column headings
        """
        self._head_tag = {None: self._default_head_tag}.get(head_tag, head_tag)
        self._header = ''.join(['<th>' + h + '</th>' for h in col_headers])
        self._footer = '</table>'
        self._rows = []

        if onclick:
            old_head = self._head_tag
            self._head_tag = '<div onclick="' + onclick + '"'
            self._head_tag += ' style="cursor:pointer">'
            self._head_tag += old_head
            self._footer = self._footer + '</div>'

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

    def add_row(self, cells, style=None, onclick=None):
        """ Adds a row of the given cells (a list of cells) and html properties.
            Ex usage: add_row([Cell('hello'), Cell('world')], onclick=DoHello())
        """
        row_str = '<tr'
        
        if not style:
            style = ''
        if onclick:
            row_str += ' onclick="' + onclick + '"'
            style = 'cursor:pointer;' + style
        if style:
            row_str += ' style="' + style + '"'

        row_str += '>'
        row_str += ''.join([str(c) for c in cells])
        row_str += '</tr>'
        
        self._rows.append(row_str)


class Cell(object):
    """ An HTML table cell.
    """
    def __init__(self, content, colspan=None, style=None):
        """ content: (str) The cell's inner content. Ex: Hello World!
            colspan: (int) HTML colspan tag content.
            style  : (str) HTML style tag content.
        """
        # Build the cell's HTML before assigning it to self
        cell_str = '<td'

        if colspan:
            cell_str += ' colspan=' + str(colspan)
        if style:
            cell_str += ' style="' + style + '"'

        cell_str += '>' + content + '</td>'
        
        self.cell = cell_str

    def __str__(self):
        """ Returns a string representation of the cell's HTML.
        """
        return self.cell


def webtime(datetime_obj):
    """ Given a datetime object, returns a string representation formatted
        according to WEBTIME_FORMAT.
    """
    if type(datetime_obj) is datetime:
        return datetime_obj.strftime(WEBTIME_FORMAT)


def get_locos_table(track):
    """ Given a track object, returns the locos html table for web display.
    """
    # Locos table is an outter table consisting of inner tables for each loco.
    outter = WebTable(col_headers=[' ID', ' Status'])

    for loco in track.locos.values():
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

        # Individual loco table onclick handler
        loco_click = "home_loco_select('" + loco.ID + "')"

        # Build inner table
        inner = WebTable(col_headers=[c for c in loco.conns.keys()])
        inner.add_row([Cell(c) for c in conn_values])       # Radio status row
        inner.add_row([Cell('<b>Last Seen Milepost/Time</b>', colspan=2)])
        inner.add_row([Cell(lastseen, colspan=2)])          # Last seen row

        outter.add_row([Cell(loco.ID), Cell(inner.html())], onclick=loco_click)

    return outter.html()


def get_loco_connline(track, loco_id):
    """ Given a track object and locomotive id string, returns a polyline
        between the locos position and connected base stations.
    """
    pass

def get_trackline(track):
    """ Returns a polyline for the given track, based on its mileposts.
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

def get_status_map(track, loco_id=None):
    """ Gets the main panel map for the given track. Adds all track devices
        to the map, except locos. If loco_id (a string) is given, then:
        If loco_id == 'ALL', all locos are added to the map. Else only the
        loco with the given ID is added.
    """
    # Containers
    map_markers = []  # Map markers, for the Google.map.markers property.
    base_points = []  # All base station points, (p1, p2). For map centering.   

    # Append markers to map_markers for
    # -- Bases:
    for base in track.bases.values():
        status_tbl = WebTable()        
        status_tbl.add_row([Cell('Device'), Cell(base.name)])
        status_tbl.add_row([Cell('Status'), Cell('OK')])
        status_tbl.add_row([Cell('Location'), Cell(str(base.coords))])
        status_tbl.add_row([Cell('Last Seen'), Cell('NA')])
        
        marker = {'icon': MAP_BASE_GRN,
                  'lat': base.coords.lat,
                  'lng': base.coords.long,
                  'infobox': status_tbl.html()}
        map_markers.append(marker)
        base_points.append((base.coords.lat, base.coords.long))

    # -- Loco(s), if given.
    if loco_id == 'ALL':
        locos = track.locos.values()
    elif loco_id:
        try:
            locos = track.locos[loco_id]
        except KeyError:
            bos_log.error('get_status_map Received an invalid loco: ' + loco_id)
            locos = []
    else:
        locos = []
    
    for loco in locos:
        status_tbl = WebTable()
        status_tbl.add_row([Cell('Device'), Cell(loco.name)])
        status_tbl.add_row([Cell('Status'), Cell('OK')])
        status_tbl.add_row([Cell('Location'), Cell(str(loco.coords))])
        status_tbl.add_row([Cell('Last Seen'), Cell('NA')])

        marker = {'icon': MAP_LOCO_GRN,
                  'lat': loco.coords.lat,
                  'lng': loco.coords.long,
                  'infobox': status_tbl.html()}
        map_markers.append(marker)

    # Determine where to center map
    if len(locos) == 1:
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
                    polylines=[get_trackline(track)])
    return panel_map

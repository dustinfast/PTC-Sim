""" PTC-Sim's web library.
"""

from flask_googlemaps import Map

from lib_app import bos_log

# HTML tag constants
HOME_SELECT_LOCO = ' Select -> '
MAP_LOCO_GRN = '/static/img/loco_ico_grn_sm.png'
MAP_LOCO_RED = '/static/img/loco_ico_red_sm.png'
MAP_LOCO_GRN_SEL = '/static/img/loco_ico_grn_sm.png'
MAP_LOCO_RED_SEL = '/static/img/loco_ico_red_sm.png'
MAP_BASE_GRN = '/static/img/base_ico_grn.png'
MAP_BASE_RED = '/static/img/base_ico_red.png'
MAP_BASE_GRN_SEL = '/static/img/base_ico_grn.png'
MAP_BASE_RED_SEL = '/static/img/base_ico_red.png'

# HTML Class constants
GRN = ''
RED = ''
YELLOW = '#dfd005'

WEBTIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class WebTable:
    """ An HTML Table, with build methods.
    """
    def __init__(self, head_tag=None, col_headers=[]):
        """ num_columns: Number of table columns
            col_headers: A list of strings representing table column headings
        """
        self._head_tag = head_tag
        self._header = ''.join(['<th>' + h + '</th>' for h in col_headers])
        self._rows = []

    def html(self):
        """ Returns an html representation of the table.
        """
        default_head_tag = '<table border="1px" style="font-size: 12px;" class="table-condensed compact nowrap table table-striped table-bordered HTMLTable no-footer" width="100%" cellspacing="0">'
        if self._head_tag:
            html_table = self._head_tag
        else:
            html_table = default_head_tag
        
        if self._header:
            html_table += '<thead><tr>'
            html_table += self._header
            html_table += '</tr></thead>'
        
        html_table += '<tbody>'
        html_table += ''.join([r for r in self._rows])
        html_table += '</tbody>'
        html_table += '</table>'

        return html_table

    def add_row(self, cells, css_class=None):
        """ Adds a row of the given cells (a list of cells) and css class.
            Ex usage: add_row([cell('hello'), cell('world')])
        """
        if css_class:
            rowstr = '<tr class="' + css_class + '">' 
        else:
            rowstr = '<tr>'
        rowstr += ''.join(cells)
        rowstr += '</tr>'

        self._rows.append(rowstr)


def cell(content, css_class=None, colspan=1):
    """ Returns an html table cell with the given content and class (strs).
    """
    td = '<td colspan=' + str(colspan) + ' '
    if css_class:
        cell = td + 'class="' + css_class + '">' + content
    cell = td + '>' + content

    return cell + '</td>'


def webtime(datetime_obj):
    """ Given a datetime object, returns a string representation formatted
        according to WEBTIME_FORMAT.
    """
    return datetime_obj.strftime(WEBTIME_FORMAT)


def get_locos_table(track):
    """ Given a track object, returns the locos html table for web display.
    """
    # Table is an outter table consisting of inner tables for each loco
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

        # Build inner table and insert it into the outter
        inner_headers = [c for c in loco.conns.keys()]      # Inner table head
        inner = WebTable(col_headers=inner_headers)         # Inner table
        inner.add_row([cell(c) for c in conn_values])       # Radio status row
        inner.add_row([cell('<b>Last Seen (Milepost @ Time)</b>', colspan=2)])
        inner.add_row([cell(lastseen, colspan=2)])          # Last seen row

        outter.add_row([cell(loco.ID),
                        cell(inner.html())])

    return outter.html()


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
    map_markers = []  # Map markers
    base_points = []  # All coord points added, (p1, p2), for centering map.   

    # -- Bases:
    for base in track.bases.values():
        status_tbl = WebTable()        
        status_tbl.add_row([cell('Device'), cell(base.name)])
        status_tbl.add_row([cell('Status'), cell('OK')])
        status_tbl.add_row([cell('Location'), cell(str(base.coords))])
        status_tbl.add_row([cell('Last Seen'), cell('NA')])
        
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
        status_tbl.add_row([cell('Device'), cell(loco.name)])
        status_tbl.add_row([cell('Status'), cell('OK')])
        status_tbl.add_row([cell('Location'), cell(str(loco.coords))])
        status_tbl.add_row([cell('Last Seen'), cell('NA')])

        marker = {'icon': MAP_LOCO_GRN,
                  'lat': loco.coords.lat,
                  'lng': loco.coords.long,
                  'infobox': status_tbl.html()}
        map_markers.append(marker)
        # print('*** ' + loco.name + ': ' + str(loco.coords) + ' @ ' + str(loco.speed))

    # Determine the centroid of all base pts, we'll center the map on that.
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

""" PTC-Sim's web library. Includes a handy html table generator.

    Author: Dustin Fast, 2018
"""

from datetime import datetime, timedelta

from lib_app import dep_install
from lib_track import CONN_TIMEOUT

# Attempt to import 3rd party modules, prompting for install on fail.
try:
    from flask_googlemaps import Map
except:
    dep_install('flask_googlemaps')


# HTML constants
GREEN = '#a0f26d'
RED = '#e60000'
YELLOW = '#dfd005'
ORANGE =  '#fe9e60'
GRAY = '#7a7a52'

# TODO: CSS class for TABLE_TAG instead of this mess
TABLE_TAG = '<table class="'
TABLE_TAG += 'table-condensed table table-striped table-bordered no-footer">'

WEBTIME_FORMAT = "%Y-%m-%d %H:%M:%S"
IMAGE_PATH = '/static/img/'

MAP_LOCO_UP = IMAGE_PATH + 'loco_ico_up.png'
MAP_LOCO_DOWN = IMAGE_PATH + 'loco_ico_down.png'
MAP_LOCO_WARN = IMAGE_PATH + 'loco_ico_warn.png'
MAP_BASE_UP = IMAGE_PATH + 'base_ico_up.png'
MAP_BASE_DOWN = IMAGE_PATH + 'base_ico_down.png'
MAP_BASE_WARN = IMAGE_PATH + 'base_ico_warn.png'
MAP_TRACKLINE_OK = GREEN
MAP_TRACKLINE_WARN = ORANGE
MAP_TRACKLINE_DOWN = RED

# CSS class name constants
UP = 'up shuffleable'
WARN = 'warn shuffleable'
DOWN = 'down shuffleable'


class Polyline(object):
    """ A representation of a geometric Polyline, for use with Google Maps.
    """
    def __init__(self, path, line_color, line_opacity=1.0, line_wt=2.0):
        self.path = path
        self.color = line_color
        self.opacity = line_opacity
        self.wt = line_wt

    def repr(self):
        """ Returns a dict representation of the polyline.
        """
        return {'stroke_color': self.color,
                'stroke_opacity': self.opacity,
                'stroke_weight': self.wt,
                'path': list(ln for ln in self.path)}


class WebTable:
    """ An HTML Table, with build methods.
    """
    _default_head_tag = TABLE_TAG
    
    def __init__(self, head_tag=None, col_headers=[], title=None):
        """ num_columns: Number of table columns
            col_headers: A list of strings representing table column headings
        """
        self.title = title
        self._head_tag = {None: self._default_head_tag}.get(head_tag, head_tag)
        self._header = ''.join(['<th>' + h + '</th>' for h in col_headers])
        self._footer = '</table>'
        self._rows = []

    def html(self):
        """ Returns an html representation of the table.
        """
        html_table = ''

        if self.title:
            html_table += '<center>' + self.title + '</center>'

        html_table += self._head_tag

        if self._header:
            html_table += '<thead><tr>'
            html_table += self._header
            html_table += '</tr></thead>'
        
        html_table += '<tbody>'
        html_table += ''.join([r for r in self._rows])
        html_table += '</tbody>'
        html_table += self._footer

        return html_table

    def add_row(self, cells, css_class=None, onclick=None, row_id=None):
        """ Adds a row of the given cells (a list of cells) and html properties.
            Ex usage: add_row([cell('hello'), cell('world')], onclick=DoHello())
        """
        row_str = '<tr'
        
        if row_id:
            row_str += ' id="' + row_id + '"'
        if not css_class:
            css_class = ''
        if onclick:
            row_str += ' onclick="' + onclick + '"'
            css_class = 'clickable ' + css_class
        if css_class:
            row_str += ' class="' + css_class + '"'

        row_str += '>'
        row_str += ''.join([c for c in cells])
        row_str += '</tr>'
        
        self._rows.append(row_str)


def cell(content, colspan=None, css_class=None, cell_id=None):
    """ Returns the given parameters as a well-formed HTML table cell tag.
        content: (str) The cell's inner content. Ex: Hello World!
        colspan: (int) HTML colspan tag content.
        css_class  : (str) HTML css class.
    """
    cell_str = '<td'

    if cell_id:
            cell_str += ' id="' + cell_id + '"'
    if colspan:
        cell_str += ' colspan=' + str(colspan)
    if css_class:
        cell_str += ' class="' + css_class + '"'

    cell_str += '>' + content + '</td>'
    
    return cell_str


def webtime(datetime_obj):
    """ Given a datetime object, returns a string representation formatted
        according to WEBTIME_FORMAT.
    """
    if type(datetime_obj) is datetime:
        return datetime_obj.strftime(WEBTIME_FORMAT)


def get_locos_table(track):
    """ Given a track object, returns two items - The locos html table (str)
         for web display, and a dict of cell IDs and their contents, from l to
         r, for use client-side to determine if shuffle txt effect applied.
         # TODO: Return html as json and render from a template instead, thus
         negating the need for the dict. 
    """
    shuffle_data = {}  # { CELLID: value }
    
    # Locos table is an outter table consisting of an inner table for each loco
    outter = WebTable(col_headers=[' ID', ' Status'])

    timenow = datetime.now()
    delta = timedelta(seconds=CONN_TIMEOUT)  # TODO: Move timeout to Connection
    for loco in sorted(track.locos.values(), key=lambda x: x.ID):
        # Connection interface row values and css class
        one_flag = False  # denotes at least one conn up
        conn_disp = {UP: [], DOWN: [], WARN: []}
        for c in loco.conns.values():
            conn_html_id = loco.name + ' ' + c.ID
            if c.conn_to:
                shuffle_data[conn_html_id] = c.conn_to.ID
                conn_disp[UP].append((conn_html_id, c.conn_to.ID))
                one_flag = True
            else:
                shuffle_data[conn_html_id] = 'N/A'

                if one_flag:
                    conn_disp[WARN].append((conn_html_id, 'N/A'))
                else:
                    conn_disp[DOWN].append((conn_html_id, 'N/A'))

        # Last seen cell value and css class
        lastseentime = track.get_lastseen(loco) 
        lastseen_html_id = loco.name + ' lastseen'
        if lastseentime:
            lastseen = str(loco.coords.marker)
            lastseen += ' @ ' + webtime(lastseentime)

            if delta < timenow - lastseentime:
                lastseen_css = DOWN
                loco.disconnect()  # TODO: Move timeout to Connection
            else:
                lastseen_css = UP
        else:
            lastseen = 'N/A'
            lastseen_css = DOWN

        shuffle_data[lastseen_html_id] = lastseen

        # Begin building inner table --
        inner = WebTable(col_headers=[c for c in loco.conns.keys()])

        # -- Connection status row
        connrow_cells = [cell(conn[1], 1, UP, conn[0]) for conn in conn_disp[UP]]
        connrow_cells += [cell(conn[1], 1, WARN, conn[0]) for conn in conn_disp[WARN]]
        connrow_cells += [cell(conn[1], 1, DOWN, conn[0]) for conn in conn_disp[DOWN]]
        max_colspan = len(connrow_cells)
        inner.add_row(connrow_cells)

        # -- Last seen row (colspan=all cols of connection status row)
        inner.add_row([cell('<b>Last Msg Recvc Time</b>', colspan=2)])
        inner.add_row([cell(lastseen, max_colspan, lastseen_css, lastseen_html_id)])

        outter.add_row([cell(loco.ID), cell(inner.html())],
                       onclick="home_select_loco('" + loco.name + "')",
                       row_id=loco.name)

    return outter.html(), shuffle_data


def get_loco_connlines(track, loco):
    """ Returns a dict of lines representing each locos base connections.
    """
    # Build loco to base connection lines
    loco_connlines = []
    for conn in [c for c in loco.conns.values() if c.connected()]:
        linepath = []
        linepath.append({'lat': loco.coords.lat + 0.2,  # TODO: scale offset to map zoom
                         'lng': loco.coords.long})
        linepath.append({'lat': conn.conn_to.coords.lat,
                         'lng': conn.conn_to.coords.long})

        loco_connlines.append(linepath)

    return loco_connlines


def get_tracklines(track):
    """ Returns a list of polylines representating the given track, based on
        its mileposts and colored according to radio coverage.
    """
    lines = []      # A list of tuples: [ (path, color), ... ]
    templines = []  # Temp container of lines: [ line, ... ]
    mps = track.mileposts_sorted  # For convenience
    
    # Aggregate mps in order, building a line for each "connected" track section
    num_mps = len(mps) - 1
    prev_conn_level = None
    for i, mp in enumerate(mps):
        conn_level = len(mp.covered_by)

        # If next item is OOB or of different level, push aggregation to lines
        if i == num_mps or len(mps[i + 1].covered_by) != conn_level:
            if prev_conn_level == 0:
                line_color = MAP_TRACKLINE_DOWN
            elif prev_conn_level == 1:
                line_color = MAP_TRACKLINE_WARN
            else:
                line_color = MAP_TRACKLINE_OK
            lines.append((templines, line_color))
            templines = []
        else:
            prev_conn_level = conn_level
            templines.append({'lat': mp.lat, 'lng': mp.long})

    # Build polylines from lines
    polylines = []
    for tup in lines:
        polylines.append(Polyline(tup[0], tup[1]).repr())
    
    return polylines  # Note: only one item in this list


def get_status_map(track, tracklines, loco=None):
    """ Gets the main status map for the given track. If not loco, all locos
        are added to the map. Else only the given loco is added.
    """
    map_markers = []  # Map markers, for the Google.map.markers property.
    base_points = []  # All base station points, (p1, p2). For map centering.   

    # Build map markers for --
    # -- Loco(s):
    if loco:
        locos = [loco]
    else:
        locos = track.locos.values()

    for l in locos:
        # Infobox contents
        tbl_title = l.name
        tbl_headers = ['MP', 'Speed', 'Direction', 'BPP']
        info_tbl = WebTable(col_headers=tbl_headers, title=tbl_title)
        info_tbl.add_row([cell(str(l.coords.marker)),
                         cell(str(l.speed)), 
                         cell(l.direction),
                         cell(str(l.bpp))])

        # Status icon
        map_icon = MAP_LOCO_UP
        if not l.connected():
            map_icon = MAP_LOCO_DOWN
        elif [c for c in l.conns.values() if not c.connected()]:
            map_icon = MAP_LOCO_WARN

        marker = {'title': l.name,
                  'icon': map_icon,
                  'lat': l.coords.lat,
                  'lng': l.coords.long,
                  'infobox': info_tbl.html()}
        map_markers.append(marker)

    # -- Bases:
    for base in track.bases.values():
        # Infobox contents
        tbl_headers = ['Location', 'Last Seen']
        info_tbl = WebTable(col_headers=tbl_headers, title=base.name)
        info_tbl.add_row([cell(str(base.coords)), cell('NA')])

        # Status icon
        map_icon = MAP_BASE_UP
        # TODO: Base down sim
        # if not base.connected():
        #     map_icon = MAP_BASE_DOWN
        # elif [c for c in base.conns.values() if not c.connected()]:
        #     map_icon = MAP_BASE_WARN

        marker = {'title': base.name,
                  'icon': map_icon,
                  'lat': base.coords.lat,
                  'lng': base.coords.long,
                  'infobox': info_tbl.html()}
        map_markers.append(marker)
        base_points.append((base.coords.lat, base.coords.long))

    # If a loco was initially passed, center the resulting map on it.
    if loco:
        center = (loco.coords.lat, loco.coords.long)
    # Else, center map on the centroid of all base station coords
    else:
        x, y = zip(*base_points)
        center = (max(x) + min(x)) / 2.0, (max(y) + min(y)) / 2.0

    status_map = Map(identifier='status_map',
                     varname='status_map',
                     lat=center[0],
                     lng=center[1],
                     maptype='SATELLITE',
                     zoom='6.5',
                     markers=list(m for m in map_markers),
                     style="height:600px;width:795px;margin:0;",
                     polylines=tracklines,
                     fit_markers_to_bounds=True)
    return status_map

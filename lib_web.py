""" PTC-Sim's web library.
"""

from flask_googlemaps import Map

from lib_app import bos_log


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


def cell(content, css_class=None):
    """ Returns an html table cell with the given content and class (strs).
    """
    if css_class:
        return '<td class='' + str(css_class) + ''>' + content + '</td>'
    return '<td>' + content + '</td>'


def get_locos_table(track):
    """ Given a track object, returns the locos html table for web display.
    """
    # The loco table is one outter table consisting of an inner table for each loco.
    select_loco_btn = ' -> '  # Temp
    outter = WebTable(col_headers=[' ID', ' Status', ' + '])  # Outter table
    for loco in track.locos.values():
        conn_values = []
        for c in loco.conns.values():
            if not c.connected_to:
                conn_values.append('N/A')
            else:
                conn_values.append(c.connected_to.ID)

        # Build inner table and insert it into the outter
        inner_headers = [c for c in loco.conns.keys()]
        inner = WebTable(col_headers=inner_headers)  # Inner table
        inner.add_row([cell(c) for c in conn_values])
        outter.add_row([cell(loco.ID),
                        cell(inner.html()),
                        cell(select_loco_btn)])

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
        'stroke_color': '#dfd005',  # Yellow
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

    # Define icons and html tags
    loco_grn = '/static/img/loco_ico_grn_sm.png'
    loco_red = '/static/img/loco_ico_red_sm.png'
    base_grn = '/static/img/base_ico_grn_sm.png'
    base_red = '/static/img/base_ico_red_sm.png'    

    # -- Bases:
    for base in track.bases.values():
        status_tbl = WebTable()        
        status_tbl.add_row([cell('Device'), cell(base.name)])
        status_tbl.add_row([cell('Status'), cell('OK')])
        status_tbl.add_row([cell('Location'), cell(str(base.coords))])
        status_tbl.add_row([cell('Last Seen'), cell('NA')])
        
        marker = {'icon': base_grn,
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

        marker = {'icon': loco_grn,
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

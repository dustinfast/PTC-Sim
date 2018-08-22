""" PTC-Sim's web library.
"""

from flask_googlemaps import Map, icons

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
        default_head_tag = '<table border="1px" class="table-condensed compact nowrap table table-striped table-bordered HTMLTable no-footer" width="100%" cellspacing="0">'
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


def get_panel_map(track, loco=None):
    """ Gets the main panel map for the given track and selected loco (if any). 
    """
    loco = track.locos.values()[0]

    panel_map = Map(
        identifier="panel_map",
        varname="panel_map",
        lat=37.4419,
        lng=-122.1419,
        # maptype = "TERRAIN",
        # zoom="5"
        markers=[
            {
                'icon': '//maps.google.com/mapfiles/ms/icons/green-dot.png',
                'lat': 37.4419,
                'lng': -122.1419,
                'infobox': "Hello I am <b style='color:green;'>GREEN</b>!"
            },
            {
                'icon': '//maps.google.com/mapfiles/ms/icons/blue-dot.png',
                'lat': 37.4300,
                'lng': -122.1400,
                'infobox': "Hello I am <b style='color:blue;'>BLUE</b>!"
            },
            {
                'icon': icons.dots.yellow,
                'title': 'Click Here',
                'lat': 37.4500,
                'lng': -122.1350,
                'infobox': (
                    "Hello I am <b style='color:#ffcc00;'>YELLOW</b>!"
                    "<h2>It is HTML title</h2>"
                    "<img src='//placehold.it/50'>"
                    "<br>Images allowed!"
                )
            }
        ],
    )

    return panel_map


if __name__ == '__main__':
    print('Printing test table:\n')
    t = WebTable()
    t.add_row([cell('Hello'), cell('World!')])
    print(t.html())

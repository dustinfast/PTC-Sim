""" PTC-Sim's web library.
"""

from subprocess import check_output

# Attempt to import simplekml and prompt for install on fail
while True:
    try:
        import simplekml
        break
    except:
        prompt = 'Simple KML is required. Run "pip install simplekml"? (Y/n): '
        install_pip = raw_input(prompt)

        if install_pip == 'Y':
            print('Installing... Please wait.')
            result = check_output('pip install flask')
            print('Success!')
        else:
            print('Exiting.')
            exit()

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
    select_loco_btn = ' -> '  # Temp
    outter = WebTable(col_headers=[' ID', ' Status', ' + '])  # Outter table
    for loco in track.locos.values():
        conn_values = []
        for c in loco.conns.values():
            if not c.connected_to:
                conn_values.append('N/A')
            else:
                conn_values.append(c.connected_to.ID)

        inner_headers = [c for c in loco.conns.keys()]
        inner = WebTable(col_headers=inner_headers)  # Inner table
        inner.add_row([cell(c) for c in conn_values])
        outter.add_row([cell(loco.ID),
                        cell(inner.html()),
                        cell(select_loco_btn)])

    return outter.html()


def get_main_panels(track):
    """ Returns a dict of loco panels: { loco_id: panel }, where panel contains
        loco status/location via KML consisting of current track restrictions,
        bases, waysides, etc. Also contains a None key, corresponding to a
        panel for the track but with no locos.
    """

    return {None: 'Click a locomotive to view control panel.'}


if __name__ == '__main__':
    print('Printing test table:\n')
    t = WebTable()
    t.add_row([cell('Hello'), cell('World!')])
    print(t.html())

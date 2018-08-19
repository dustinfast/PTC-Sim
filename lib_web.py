

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


if __name__ == '__main__':
    print('Printing test table:\n')
    t = WebTable()
    t.add_row([cell('Hello'), cell('World!')])
    print(t.html())
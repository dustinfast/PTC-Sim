import simplekml

from lib_track import Track

HOSTNAME = 'localhost:5000'

def panel_kml(loco):
    kml = simplekml.Kml()

    # loco status table
    status_table = '<body><center><table style= "font-family: Arial; color: black; font-size: 16px;" border="1px">'
    status_table += '<tr><td>test</td></tr>'
    status_table += '</table></center></body>'

    pointstyle = simplekml.Style()
    pointstyle.iconstyle.icon.href = 'http://' +  HOSTNAME + '/static/kml/loco.png'

    locopoint = kml.newpoint(name=(loco.ID),
                             description="<![CDATA[" + status_table + "]]>",
                             coords=[(str(loco.coords.long) + ',' + str(loco.coords.lat))])
    locopoint.style = pointstyle
    locopoint.iconstyle.heading = "0"
    locopoint.iconstyle.scale = 3

    return kml


if __name__ == '__main__':
    # Build loco kmls, including all bases, waysides, etc. With highlights for
    # bases connected to current loco
    track = Track()
    for loco in track.locos.values():
        print('Writing kml for ' + loco.name)
        kml = panel_kml(loco)
        kml.save("kml/" + str(loco.ID) + ".kml")       
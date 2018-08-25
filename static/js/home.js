/* The javascript library for PTC-Sim's "Home" page.
 * 
 * Author: Dustin Fast, 2018
*/

// Constants
var SEL_BORDERSTYLE = 'solid thick';
var LOCO_CONNLINE = {
    path: 'M 0,-1 0,1',
    strokeOpacity: .6,
    strokeColor: '#99ff66',
    scale: 2
};

// Page state vars
var curr_loco_name = null;     // Currently selected loco in the locos table
var may_persist_loco = null;  // Loco w/infobox to persist bteween refreshes
var open_infobox_markers = {}; // Markers w/infoboxes to persist btwn refreshes
var curr_polylines = [];

// Locos table loco click handler - If selecting same loco as prev selected, 
// toggles selection off, else sets the selected loco as the new selection.
function loco_select_onclick(loco_name) {
    // Handle updating the persist var
    old_may_persist = may_persist_loco;
    if (!may_persist_loco && !curr_loco_name) {
        may_persist_loco = loco_name;
        // console.log('set persist1: ' + may_persist_loco);
    } else if (curr_loco_name && may_persist_loco != curr_loco_name) {
        may_persist_loco = null;
        // console.log('set persist2: ' + may_persist_loco);
    } else if (curr_loco_name) {
        may_persist_loco = curr_loco_name;
        // console.log('set persist3: ' + may_persist_loco);
    }

    if (curr_loco_name == loco_name) {
        curr_loco_name = null;
        // console.log('set curr1: ' + curr_loco_name)
    } else {
        curr_loco_name = loco_name;
        // console.log('set curr2: ' + curr_loco_name)
    }

    home_get_content_async(); // Refresh the content
}
    
// Refresh the status/overview map, including all bases, lines, etc. Further, if 
// curr_loco_name is null, all locos are included in the refreshed map. Else,
// only that loco is included in the refreshed version.
// Note: Can't seem to get JQuery shorthand working here (trashes the JSON).
function home_get_content_async() {
    $.ajax({
        url: $SCRIPT_ROOT + '/_home_get_async_content',
        type: 'POST',
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify({ 'loco_name': curr_loco_name }),

        success: function (data) {
            if (data == 'error') {
                console.error('Server returned error fetching status map.')
                return;
            }
            start_time = performance.now();  // debug

            
            
            // Remove all existing map markers and polylines
            panel_map_markers.forEach(function (marker) {
                    marker.setMap(null);
                });
            panel_map_markers = []

            curr_polylines.forEach(function (pline) {
                pline.setMap(null);
            });
            curr_polylines = []

            // Set map's loco connection lines as polylines, if any
            $.each(data.loco_connlines, function (i) {
                console.log(data.loco_connlines[i])
                var line = new google.maps.Polyline({
                    path: data.loco_connlines[i],
                    strokeOpacity: 0,
                    icons: [{
                        icon: LOCO_CONNLINE,
                        offset: '0px',
                        repeat: '10px'
                    }],
                    map: panel_map
                });
                curr_polylines.push(line)
            });
            
            // Set maps markers
            $.each(data.status_map.markers, function (i) {
                // Note that marker_title matches curr_loco's table ID.
                var marker_title = data.status_map.markers[i].title

                // Init the marker object
                var marker = new google.maps.Marker({
                    position: new google.maps.LatLng(
                        data.status_map.markers[i].lat,
                        data.status_map.markers[i].lng
                    ),
                    icon: data.status_map.markers[i].icon,
                    title: marker_title,
                    map: panel_map  // TODO: status_map
                });
                
                // Marker's infobox. Note that it is never explicitly attached.
                var infowindow = new google.maps.InfoWindow({
                    content: data.status_map.markers[i].infobox
                });
                
                // Marker's infobox "onopen" handler
                marker.addListener('click', function () {
                    infowindow.open(panel_map, marker);
                    open_infobox_markers[marker_title] = marker;  // set persist
                });

                // Marker's infobox "onclose" handler
                google.maps.event.addListener(infowindow, 'closeclick', function () {
                    delete open_infobox_markers[marker_title]; // unset persist
                });

                // Push the new marker to the map's list of markers
                panel_map_markers.push(marker);
                
                // Handle infobox persistence, based on open_infobox_markers
               if (open_infobox_markers.hasOwnProperty(marker_title)) {
                    is_loco = marker_title.includes('Loco ')
                   if (is_loco && marker_title == may_persist_loco) {
                        // It's the persisting loco
                        infowindow.open(panel_map, marker);
                    } else if (is_loco) {
                        // Ditch ref so no reopen of unselected loco infoboxes
                        console.log('removing: ' + marker_title);
                        delete open_infobox_markers[marker_title]
                    } else if (!is_loco) {
                        // We reopen all other device type infoboxes
                        infowindow.open(panel_map, marker);
                    }
                }
            });

            // Set new locos_table content and update selection border
            $('#locos_table').html(data.locos_table);
            if (curr_loco_name) {
                document.getElementById(curr_loco_name).style.border = SEL_BORDERSTYLE;
            }

            duration = performance.now() - start_time;
            console.log('Content Refreshed - client side took: ' + duration);
        }
    });
}

// Refreshes locos table & status map immediately, then again at given interval.
function home_update_content_async(refresh_interval=60000) {
    // home_get_locotable_async();
    home_get_content_async();
    setInterval(function () {
        // home_get_locotable_async();
        home_get_content_async();
    }, refresh_interval);
}

// AJAX GET
// function home_get_map_async() {
//     $.getJSON($SCRIPT_ROOT + '/_home_map_update',
//         function (data) {
//             console.log(data.status_map.markers)
//             });
//         });
// }

// AJAX POST
// function home_loco_select(locoID) {
//     $.ajax({
//         url: $SCRIPT_ROOT + '/_home_select_loco',
//         type: 'POST',
//         contentType: 'application/json;charset=UTF-8',
//         data: JSON.stringify({ 'locoID': locoID }),
//         success: function () {
//             console.log('success');
//         }
//     });
// }


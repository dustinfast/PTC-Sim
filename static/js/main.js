/* The javascript library for PTC-Sim's "Home" page.
 * 
 * Author: Dustin Fast, 2018
*/

// Constants
var SEL_BORDERSTYLE = 'solid thick';

// Page state vars
var curr_loco_name = null;     // Currently selected loco (in the locos table)
var open_infobox_markers = {}; // Markers w/infoboxes to persist btwn refreshes

// TODO: main.js to bos_web_home.js, main.js to bos_web.js

// Locos table loco click handler - If selecting same loco as prev selected, 
// toggles selection off, else sets the selected loco as the new selection.
function loco_select_onclick(loco_name) {
    if (curr_loco_name == loco_name) {
        curr_loco_name = null;
    } else {
        curr_loco_name = loco_name;
    }
    home_get_statusmap_async(); // Refresh the content
}

// Updates the locos table
// function home_get_locotable_async() {
//     $.getJSON(
//         $SCRIPT_ROOT + '/_home_get_locotable',
//         function (table_data) {
//             // Update locos_table div from received data
//             $('#locos_table').html(table_data.locos_table);
//         });
//     // Update currently selected loco's table border 
//     if (curr_loco_name) {
//         console.log(document.getElementById(curr_loco_name).style.border);
//         document.getElementById(curr_loco_name).style.border = SEL_BORDERSTYLE;
//     }
//     }
    
// Refresh the status/overview map, including all bases, lines, etc. Further, if 
// curr_loco_name is null, all locos are included in the refreshed map. Else,
// only that loco is included in the refreshed version.
// Note: Can't seem to get JQuery shorthand working here (trashes the JSON).
function home_get_statusmap_async() {
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

            /// Set new locos_table content and update selection border
            $('#locos_table').html(data.locos_table);
            if (curr_loco_name) {
                console.log(document.getElementById(curr_loco_name).style.border);
                document.getElementById(curr_loco_name).style.border = SEL_BORDERSTYLE;
            }
            
            // Remove all existing status map markers // TODO: Rem all existing lines
            panel_map_markers.forEach(function (marker) {
                    marker.setMap(null);
                });
            panel_map_markers = []

            // Add new markers to the status map, based on received data.
            $.each(data.status_map.markers, function (i) {
                // Note that marker titles match the devices's inner table ID.
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
                    if (is_loco && marker_title == curr_loco_name) {
                        console.log('is loco')
                        // It's the currently selected loco
                        infowindow.open(panel_map, marker);
                    } else if (is_loco) {
                        // Ditch ref so no reopen of unselected loco infoboxes
                        console.log('removing: ' + marker_title);
                        delete open_infobox_markers[marker_title]
                    } else if (!is_loco) {
                        console.log('not loco')
                        // We reopen all other device type infoboxes
                        infowindow.open(panel_map, marker);
                    }
                }
            });

            // TODO: recenter map. panel_map.center?

            duration = performance.now() - start_time;
            console.log('Content Refreshed - client side took: ' + duration);
        }
    });
}

// Refreshes locos table & status map immediately, then again at given interval.
function home_update_content_async(refresh_interval=60000) {
    // home_get_locotable_async();
    home_get_statusmap_async();
    setInterval(function () {
        // home_get_locotable_async();
        home_get_statusmap_async();
    }, refresh_interval);
}

// Working AJAX GET
// function home_get_map_async() {
//     $.getJSON($SCRIPT_ROOT + '/_home_map_update',
//         function (data) {
//             console.log(data.status_map.markers)
//             });
//         });
// }

// Working AJAX POST
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


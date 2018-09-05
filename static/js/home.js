/* The javascript for PTC-Sim's home.html
* 
* Author: Dustin Fast, 2018
*/

// Consts
LOCO_SVG = 'M 450.288 356.851 l -47.455 -34.558 c 24.679 -16.312 40.427 -44.298 40.427 -74.996 c 0 -45.823 -34.494 -83.743 -78.881 -89.157 V 78.077 h 3.982 c 3.036 0 6.199 -2.463 6.199 -5.5 v -12 c 0 -3.037 -3.163 -5.5 -6.199 -5.5 h -71.667 c -3.036 0 -5.5 2.463 -5.5 5.5 v 12 c 0 3.037 2.464 5.5 5.5 5.5 h 4.688 v 79.401 h -108.44 V 83.704 c 0 -8.284 -6.716 -15 -15 -15 H 15.001 c -5.873 0 -11.205 3.427 -13.645 8.769 c -2.44 5.342 -1.537 11.616 2.309 16.055 l 34.426 39.73 v 188.86 c 0 7.484 5.488 13.671 12.656 14.799 c 1.255 35.758 30.717 64.465 66.773 64.465 c 31.693 0 58.285 -22.184 65.114 -51.833 h 47.324 c 6.829 29.649 33.421 51.833 65.113 51.833 c 17.285 0 33.06 -6.598 44.937 -17.404 h 101.448 c 6.495 0 12.254 -4.182 14.265 -10.357 C 457.731 367.442 455.539 360.674 450.288 356.851 Z M 117.521 349.548 h 25.471 c -5.15 8.713 -14.637 14.573 -25.471 14.573 c -16.307 0 -29.574 -13.269 -29.574 -29.574 s 13.268 -29.571 29.574 -29.571 c 10.834 0 20.321 5.859 25.472 14.572 h -25.472 c -8.284 0 -15 6.717 -15 15 C 102.521 342.832 109.237 349.548 117.521 349.548 Z M 152.744 199.595 H 78.449 v -90 h 74.295 V 199.595 Z M 295.073 364.122 c -10.834 0 -20.319 -5.859 -25.471 -14.573 h 25.469 c 8.284 0 15 -6.716 15 -15 s -6.716 -15 -15 -15 h -25.47 c 5.15 -8.713 14.638 -14.573 25.472 -14.573 c 16.307 0 29.571 13.268 29.571 29.572 C 324.645 350.854 311.379 364.122 295.073 364.122 Z';
LOCO_CONNLINE = {
    path: 'M 0, -2 1, 1',
    strokeOpacity: .8,
    strokeColor: '#ffff00', // Yellow
    scale: 2
};
LOCO_NO_CONNLINE = {
    path: 'M 0,-1 0,1',
    strokeOpacity: .6,
    strokeColor: '#ff0000', // Red
    scale: 2
};

// Globals
var curr_loco = null;           // Selected loco. Ex: 'Loco 1001'
var curr_polylines = [];        // A list of all visible map polylines
var time_icand = 1              // Simulation speed multiplicand
var refresh_interval = 5000     // Async refresh interval
var on_interval = null;         // Ref to the active setInterval function
var persist_infobox = null;     // The map infobox to persist between refreshes

// A Maps infobox & associated marker that persists across async updates.
class PersistInfobox {
    constructor() {
        this.clear();
    }
    set(infobox, marker, map) {
        this._infobox = infobox,
        this._marker = marker
    }
    clear() {
        this._infobox = null,
        this._marker = null
    }
    open(map) {
        if (this._infobox) {
            this._infobox.open(map, this._marker);
        }
    }
    close() {
        if (this._infobox) {
            this._infobox.close();
            this.clear();
        }
    }
    is_for_device(device_name) { 
       return (this._marker && this._marker.title == device_name)
    }
    is_loco () {
        return (this._marker && this._marker.title.includes('Loco'))
    }
}
persist_infobox = new PersistInfobox();


// Define listeners and start async content refresh
$(document).ready(function () {
    var time_slider =
        $('#temporal-range').on('input', function () {
            main_set_sessionvar_async('time_icand', $(this).val() / 100); // % to decimal
            doCPViewUpdate();
        });

    var refresh_slider = $('#refresh-range');
    refresh_slider.on('input', function () {
        clearInterval(on_interval);                             // Nullify current interval
        on_interval = setAsynchInterval($(this).val() * 1000);  // Start new interval (s to ms)
        doCPViewUpdate();

    });

    // Start asynch refresh, noting the interval so it can be cleared later.
    on_interval = setAsynchInterval(refresh_slider.val() * 1000) // s to ms
    doCPViewUpdate();
});


// Locos table click handler -
// Onclick currently selected loco, toggles selection off, else toggle it on.
function locosTableOnclick(loco_name) {
    if (curr_loco == loco_name) {
        curr_loco = null;
    } else {
        curr_loco = loco_name;

        // If selected a loco and another's infobox is open, clear it.
        if (persist_infobox.is_loco() && !persist_infobox.is_for_device(loco_name)) {
            persist_infobox.close();
        }
    }

    updateContentAsync(); // Refresh the page's dynamic content
}


// Refresh pages asynchronous content -
// If curr_loco, only that loco is shown. Else, all locos shown
// Note: Don't use JQuery shorthand here, it trashes the JSON.
function updateContentAsync() {
    $.ajax({
        url: $SCRIPT_ROOT + '/_home_get_async_content',
        type: 'POST',
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify({ 'loco_name': curr_loco }),
        timeout: 1000,

        error: function (jqXHR, textStatus, errorThrown) {
                console.warn('Error contacting server for content refresh.');
        },

        success: function (data) {
            if (data == 'error') {
                console.warn('Server-server content refresh error.')
                return;
            }
            start_time = performance.now();  // debug

            // Note fields for txt shuffle if having new data since last refresh
            needs_txtshuffle = []
            $('.shuffleable').each(function (i, obj) {
                id = $(this).attr('id')
                if ($(this).text() != data.shuffle_data[id]) {
                    needs_txtshuffle.push(id);
                }
            });
            
            // Refresh locos table, setting loco selection border if needed
            $('#locos-table').html(data.locos_table);
            if (curr_loco) {
                document.getElementById(curr_loco).className = 'clicked';
            }

            // Do txt shuffle effect for each element id in needs_txtshuffle
            $('.shuffleable').each(function (i, obj) {
                if (needs_txtshuffle.indexOf($(this).attr('id')) != -1) {
                    $(this).shuffleLetters({
                        'step': 6,
                        'fps': 35
                    });
                }
            });

            //Remove all existing map markers & polylines before we replace them
            status_map_markers.forEach(function (marker) {
                    marker.setMap(null);
                });
            status_map_markers = []

            curr_polylines.forEach(function (pline) {
                pline.setMap(null);
            });
            curr_polylines = []

            // Add loco conn polylines to map
            $.each(data.loco_connlines, function (i) {
                var line = new google.maps.Polyline({
                    path: data.loco_connlines[i],
                    strokeOpacity: 0,
                    icons: [{
                        icon: LOCO_CONNLINE,
                        offset: '0px',
                        repeat: '10px'
                    }],
                    map: status_map
                });
                curr_polylines.push(line)
            });
            
            // Set map loco and base markers
            $.each(data.status_map.markers, function (i) {
                // Note: marker_title matches curr_loco's table ID.
                var marker_title = data.status_map.markers[i].title
                var marker_icon = data.status_map.markers[i].icon
                is_draggable = false;  // Non-loco icons are not draggable

                // Loco icons are SVG and get rotated for heading
                if (marker_title.includes('Loco')) {
                    is_draggable = true;
                    
                    // Adjust anchor based on rotation so it sits on trackline
                    rotate_deg = data.status_map.markers[i].rotation - 90;
                    anchor_x = 250; anchor_y = 0;
                    
                    // TODO: Adjust anchor for each possible degree
                    console.log(marker_title + ': ' + rotate_deg.toString());
                    if (rotate_deg == -90) {
                        anchor_y += 200  // seems good
                    } else if (rotate_deg == -45) {
                        anchor_x -= 30;
                    } else if (rotate_deg == 0) {
                        anchor_x -= 200;
                    } else if (rotate_deg == 45) {
                        anchor_x += 20;
                        anchor_y += 200;
                    } else if (rotate_deg == 90) {
                        anchor_x -= 50;  // seems good
                    } else if (rotate_deg == 135) {
                    } else if (rotate_deg == 180) {
                    } else if (rotate_deg == 225) {
                        anchor_x += 100
                        anchor_y += 200
                    } else if (rotate_deg == 270) {
                        anchor_y += 200 // seems good
                    } else {
                        console.warn('Unhandled rotation: ' + rotate_deg.toString());
                    }
                        
                    marker_icon = {
                        path: LOCO_SVG,
                        // origin: new google.maps.Point(0, 0),
                        anchor: new google.maps.Point(anchor_y, anchor_x),
                        rotation: rotate_deg,
                        fillOpacity: 0.9,
                        scale: .07,
                        strokeColor: 'black',
                        fillColor: data.status_map.markers[i].status,
                        strokeWeight: 1,
                    }
                }
                
                // Init the marker object
                var marker = new google.maps.Marker({
                    position: new google.maps.LatLng(
                        data.status_map.markers[i].lat,
                        data.status_map.markers[i].lng
                    ),
                    icon: marker_icon,
                    title: marker_title,
                    draggable: is_draggable, // TODO: helicoptering
                    map: status_map
                });
                
                // Marker's infobox. Note it is only 'attached' on open
                var infobox = new google.maps.InfoWindow({
                    content: data.status_map.markers[i].infobox,
                });

                // Define onclick behavior for the marker (toggle open/close)
                // Note that we only ever allow one open infobox at a time
                marker.addListener('click', function () {
                    if (persist_infobox.is_for_device(marker.title)) {
                        persist_infobox.close();
                    } else {
                        persist_infobox.close();
                        persist_infobox.set(infobox, marker); 
                        persist_infobox.open(status_map);
                    }
                });

                status_map_markers.push(marker); // Attach new marker to the map
            });

            // Reopen current persisting infobox, if any
            persist_infobox.open(status_map)
            
            // debug
            duration = performance.now() - start_time;
            console.log('Home Refreshed - client side took: ' + duration);
        }
    });
}


// The setInterval handler. Returns a ref to the actual setInterval()
function setAsynchInterval (refresh_interval) {
    updateContentAsync();
        var setinterval = setInterval(function () {
            updateContentAsync();
    }, refresh_interval);
    
    return setinterval;
}


function doCPViewUpdate() {
    $('#time-icand').html('&nbsp;' + $('#temporal-range').val() + '%');
    $('#refresh-val').html('&nbsp;' + $('#refresh-range').val() + 's');
}

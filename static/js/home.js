// The javascript library for PTC-Sim's "Home" page.
// 
/// Author: Dustin Fast, 2018


// Constants
var LOCO_CONNLINE = {
    path: 'M 0, -2 1, 1',
    strokeOpacity: .6,
    strokeColor: '#99ff66', // Green
    scale: 2
};

var LOCO_NO_CONNLINE = {
    path: 'M 0,-1 0,1',
    strokeOpacity: .6,
    strokeColor: '#ff0000', // Red
    scale: 2
};

// Page state and obj refs
var curr_loco_name = null;     // Currently selected loco in the locos table
var may_persist_loco = null;   // Loco w/infobox to persist bteween refreshes
var open_infobox_markers = {}; // Markers w/infoboxes to persist btwn refreshes
var curr_polylines = [];       // A list of all visible status map polylines
var time_icand = 1             // Simulation speed multiplier, 1 to 10,
var refresh_interval = 5000    // AJAX call interval. Defines status resolution
var on_interval = null;        // Ref  to setInterval function, for clearing it


// Locos table loco click handler - If selecting same loco as prev selected, 
// toggles selection off, else sets the selected loco as the new selection.
function home_select_loco(loco_name) {
    // Handle updating the persist var
    old_may_persist = may_persist_loco;
    if (!may_persist_loco && !curr_loco_name) {
        may_persist_loco = loco_name;
        // console.log('set persist1: ' + may_persist_loco);  //debug
    } else if (curr_loco_name && may_persist_loco != curr_loco_name) {
        may_persist_loco = null;
        // console.log('set persist2: ' + may_persist_loco);  //debug
    } else if (curr_loco_name) {
        may_persist_loco = curr_loco_name;
        // console.log('set persist3: ' + may_persist_loco);  //debug
    }

    if (curr_loco_name == loco_name) {
        curr_loco_name = null;
        // console.log('set curr1: ' + curr_loco_name);  //debug
    } else {
        curr_loco_name = loco_name;
        // console.log('set curr2: ' + curr_loco_name);  //debug
    }

    _get_content_async(); // Refresh the pages dynamic content
}
    
// Refresh the status/overview map, including all bases, lines, etc. Further, if 
// curr_loco_name is null, all locos are included in the refreshed map. Else,
// only that loco is included in the refreshed version.
// Note: Can't seem to get JQuery shorthand working here (trashes the JSON).
function _get_content_async() {
    $.ajax({
        url: $SCRIPT_ROOT + '/_home_get_async_content',
        type: 'POST',
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify({ 'loco_name': curr_loco_name }),
        timeout: 1000,

        error: function (jqXHR, textStatus, errorThrown) { //TODO: declare in main.js
            if (textStatus === "timeout") {
                console.log('Content refresh timed out wait for server.');
            }
        },

        success: function (data) {
            if (data == 'error') {
                console.error('Server returned error fetching status map.')
                return;
            }
            start_time = performance.now();  // debug

            // Refresh locos table and update loco selection border if needed
            $('#locos-table').html(data.locos_table);
            if (curr_loco_name) {
                document.getElementById(curr_loco_name).className = 'clicked';
            }

            // Rm all existing map markers and polylines before we replace them
            status_map_markers.forEach(function (marker) {
                    marker.setMap(null);
                });
            status_map_markers = []

            curr_polylines.forEach(function (pline) {
                pline.setMap(null);
            });
            curr_polylines = []

            // Set map's loco connection lines as polylines, if any
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
                    map: status_map  // TODO: status_map
                });
                
                // Marker's infobox. Note that it is never explicitly attached
                // and may be "opened" for more than one marker or location.
                var infowindow = new google.maps.InfoWindow({
                    content: data.status_map.markers[i].infobox
                });
                
                // Regerister for marker's infobox "on open"
                marker.addListener('click', function () {
                    infowindow.open(status_map, marker);
                    open_infobox_markers[marker_title] = marker;  // set persist
                });

                // Register for infobox's "on close" 
                google.maps.event.addListener(infowindow, 'closeclick', function () {
                    delete open_infobox_markers[marker_title]; // unset persist
                });

                // Push the new marker to the map's list of markers
                status_map_markers.push(marker);
                
                // Handle infobox persistence, based on open_infobox_markers
               if (open_infobox_markers.hasOwnProperty(marker_title)) {
                    is_loco = marker_title.includes('Loco ')
                   if (is_loco && marker_title == may_persist_loco) {
                        // It's the persisting loco
                        infowindow.open(status_map, marker);
                    } else if (is_loco) {
                        // Ditch ref so no reopen of unselected loco infoboxes
                        delete open_infobox_markers[marker_title]
                    } else if (!is_loco) {
                        // We reopen all other previously open non-loco infoboxes
                        infowindow.open(status_map, marker);
                    }
                }
            });

            // Reference map for use outside this context
            map = status_map
            
            duration = performance.now() - start_time;
            console.log('Home Refreshed - client side took: ' + duration);
        }
    });
}

function _build_maplegend() {
    // TODO: Build legend server-side
    imgpath = '/static/img/'
    var icons = {
        greenline: {
            name: 'Two (or more) 220 MHz bases',
            icon: imgpath + 'greenline.png'
        },
        orangline: {
            name: 'Single 220 MHz base',
            icon: imgpath + 'orangeline.png'
        },
        redline: {
            name: 'None',
            icon: imgpath + 'redline.png'
        }
    };

    var legend = document.getElementById('map-legend');
    legend.innerHTML += '&nbsp;<b>Coverage Legend</b>: '
    for (var key in icons) {
        var type = icons[key];
        var name = type.name;
        var icon = type.icon;
        legend.innerHTML += name + ': <img src="' + icon + '"> &nbsp;&nbsp;&nbsp;&nbsp;';
    }
}

// The setInterval handler. Retruns a ref to the actual setInterval()
function _async_interval (refresh_interval) {
        var setinterval = setInterval(function () {
            _get_content_async();
    }, refresh_interval);

    // Update control panel refresh interval display
    disp_val = refresh_interval / 1000  // Back to seconds for display
    document.getElementById('refresh-val').innerHTML = '&nbsp;' + disp_val + 's';

    return setinterval;
}

// Called at the end of main.html: Registers listeners then calls _async_interval()
function home_start_async() {
    // Register slider onchange listeners and define their behavior
    var time_slider = document.getElementById("temporal-range")
    var refresh_slider = document.getElementById("refresh-range");
    time_disp = refresh_slider.value + '%';
    refresh_disp = refresh_slider.value + 's';

    time_slider.oninput = function () {
       new_val = this.value / 100              // Convert percent to decimal
       main_set_sessionvar_async('time_icand', new_val); // from main.js
       document.getElementById('time-icand').innerHTML = '&nbsp;' + this.value + '%';
    }
    refresh_slider.oninput = function () {
        new_val = this.value * 1000             // Convert to ms
        clearInterval(on_interval);             // Stop current setInterval
        on_interval = _async_interval(new_val); // Start new setInterval
    }

    _build_maplegend(); // Init the map legend

    // Get the main content and update the page
    _get_content_async();
    on_interval = _async_interval(refresh_slider.value * 1000) // Converting to ms
    document.getElementById('time-icand').innerHTML = '&nbsp;' + time_slider.value + '%';
    document.getElementById('refresh-val').innerHTML = '&nbsp;' + refresh_slider.value + 's';
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


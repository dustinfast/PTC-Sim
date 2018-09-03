/* The javascript for PTC-Sim's home.html
* 
* Author: Dustin Fast, 2018
*/

// Constants
var LOCO_CONNLINE = {
    path: 'M 0, -2 1, 1',
    strokeOpacity: .8,
    strokeColor: '#ffff00', // Yellow
    scale: 2
};

var LOCO_NO_CONNLINE = {
    path: 'M 0,-1 0,1',
    strokeOpacity: .6,
    strokeColor: '#ff0000', // Red
    scale: 2
};

// Globals
var curr_loco = null;          // Selected locos table loco. Ex: 'Loco 1001'
var curr_polylines = [];       // A list of all visible status map polylines
var time_icand = 1             // Simulation speed multiplicand
var refresh_interval = 5000    // async refresh interval / max status resolution
var on_interval = null;        // Ref to setInterval function, for clearing it
var persist_infobox = null; // The map infobox to persist btween refreshes


// A Google maps infobox with associated marker. 
// Handles persisting across asynchronous page content updates.
class PersistInfobox {
    constructor(infobox=null, marker=null) {
        this.infobox = infobox,
        this.marker = marker
    }

    set(infobox, marker, map) {
        this.infobox = infobox,
        this.marker = marker
    }

    clear() {
        this.infobox = null,
        this.marker = null
    }

    is_set() {
        return (!this.infobox);
    }

    open(map) {
        if (this.infobox) {
            this.infobox.open(map, this.marker);
        }
    }

    close() {
        if (this.infobox) {
            this.infobox.close();
            this.clear();
        }
    }

    is_for_device(device_name) { 
       return (this.marker && this.marker.title == device_name)
    }
    
    is_loco () {
        return (this.marker && this.marker.title.includes('Loco'))
    }
}
persist_infobox = new PersistInfobox();

// Locos table click handler -
// If clicking currently selected loco, toggles selection off, else toggle it on
function home_select_loco(loco_name) {
    if (curr_loco == loco_name) {
        curr_loco = null;
    } else {
        curr_loco = loco_name;

        // If selecting a loco but another loco's infobox is open, clear it.
        if (persist_infobox.is_loco() && !persist_infobox.is_for_device(loco_name)) {
            persist_infobox.close();
        }
    }

    _update_content_async(); // Refresh the pages dynamic content
}
    
// Refresh pages asynchronous content -
// If curr_loco, only that loco is shown. Else, all locos shown
// Note: Can't seem to get JQuery shorthand working in ajax call (JSON trashed)
function _update_content_async() {
    $.ajax({
        url: $SCRIPT_ROOT + '/_home_get_async_content',
        type: 'POST',
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify({ 'loco_name': curr_loco }),
        timeout: 1000,

        error: function (jqXHR, textStatus, errorThrown) {
            if (textStatus === 'timeout') {
                console.log('Content refresh request timed out.');
            }
        },

        success: function (data) {
            if (data == 'error') {
                console.error('Server available but failed returning content.')
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

            // Rm all existing map markers and polylines before we replace them
            status_map_markers.forEach(function (marker) {
                    marker.setMap(null);
                });
            status_map_markers = []

            curr_polylines.forEach(function (pline) {
                pline.setMap(null);
            });
            curr_polylines = []

            // Create loco conn polylines
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

                // Init the marker object
                var marker = new google.maps.Marker({
                    position: new google.maps.LatLng(
                        data.status_map.markers[i].lat,
                        data.status_map.markers[i].lng
                    ),
                    icon: data.status_map.markers[i].icon,
                    title: marker_title,
                    map: status_map
                    // TODO: heading
                });
                
                // Marker's infobox. Note it is only 'attached' on open
                var infobox = new google.maps.InfoWindow({
                    content: data.status_map.markers[i].infobox,
                });

                // Define onclick behavior for the marker (toggle open/close)
                // Note that we only ever allow one open infobox at a time
                marker.addListener('click', function () {
                    // if this infobox is currently open, close it
                    if (persist_infobox.is_for_device(marker.title)) {
                        persist_infobox.close();
                    // else, open it, closing the open one first, if any
                    } else {
                        persist_infobox.close();
                        persist_infobox.set(infobox, marker); 
                        persist_infobox.open(status_map);
                    }
                });

                // Push the new marker to the map
                status_map_markers.push(marker);
            });

            // Reopen the persisting infobox, if any
            persist_infobox.open(status_map)
            
            // debug
            duration = performance.now() - start_time;
            console.log('Home Refreshed - client side took: ' + duration);
        }
    });
}

function _build_maplegend() {
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
            _update_content_async();
    }, refresh_interval);

    // Update control panel refresh interval display
    disp_val = refresh_interval / 1000  // Back to seconds for display
    $('#refresh-val').html('&nbsp;' + disp_val + 's');
    return setinterval;
}

// Called at the end of main.html: Registers listeners then calls _async_interval()
function home_start_async() {
    // Register slider onchange listeners and define their behavior
    var time_slider = $('#temporal-range')
    var refresh_slider = $('#refresh-range');
    time_disp = refresh_slider.val() + '%';
    refresh_disp = refresh_slider.val() + 's';

    time_slider.on('input', function () {
       new_val = $(this).val() / 100              // Convert percent to decimal
       main_set_sessionvar_async('time_icand', new_val); // from main.js
        $('#time-icand').html('&nbsp;' + $(this).val() + '%');
    });
    refresh_slider.on('input', function () {
        new_val = $(this).val() * 1000             // Convert to ms
        clearInterval(on_interval);             // Stop current setInterval
        on_interval = _async_interval(new_val); // Start new setInterval
    });

    _build_maplegend(); // Init the map legend

    // Get the main content and update the page
    _update_content_async();
    on_interval = _async_interval(refresh_slider.val() * 1000) // Converting to ms
    $('#time-icand').html('&nbsp;' + time_slider.val() + '%');
    $('#refresh-val').html('&nbsp;' + refresh_slider.val() + 's');
}

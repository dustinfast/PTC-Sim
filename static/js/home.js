/* The javascript for PTC-Sim's home.html
* 
* Author: Dustin Fast, 2018
*/

// Consts
var IMG_PATH = '/static/img/'
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
var curr_loco = null;           // Selected loco. Ex: 'Loco 1001'
var curr_polylines = [];        // A list of all visible map polylines
var time_icand = 1              // Simulation speed multiplicand
var refresh_interval = 5000     // Async refresh interval
var on_interval = null;         // Ref to the active setInterval function
var persist_infobox = null;     // The map infobox to persist between refreshes
var prev_marker_icons = {}      // i'th refresh's icons, to use at refresh i + 1


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

            // Remove all existing map markers & polylines before we replace them
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
                is_draggable = false;

                // Loco icons get rotated according to heading and are draggable
                if (marker_title.includes('Loco')) {
                    is_draggable = true;
                    // Save this loco's icon to use during the next refresh to
                    // avoid late img load issues.
                    // TODO: Load images once and re-use them.
                    loadImage(marker_icon)
                        .then((img) => {
                            canvas = document.createElement('canvas');
                            canvas.width = img.width;
                            canvas.height = img.height;

                            center_x = img.width / 2;
                            center_y = img.height / 2;
                            
                            context = canvas.getContext('2d');
                            context.clearRect(0, 0, img.width, img.height);
                            context.save();          // Push context state
                            context.translate(center_x, center_y);
                            context.rotate(data.status_map.markers[i].rotation);
                            context.translate(-center_x, -center_y);
                            context.drawImage(img, 0, 0);
                            context.restore();       // Pop context state

                            rotated_url = canvas.toDataURL();
                            rotated_icon = {
                                url: rotated_url,
                                origin: new google.maps.Point(0, 0),  // image origin
                                // anchor: new google.maps.Point(22, 44)  // from origin
                            }
                            prev_marker_icons[marker_title] = rotated_icon;
                        })
                        .catch(error => console.error('ERROR: ' + error));
                            
                    // Populated the current loco icon by consuming it's prev icon
                    if (prev_marker_icons.hasOwnProperty(marker_title)) {
                        // Attempt to close previous icon
                        marker_icon = prev_marker_icons[marker_title];
                        delete prev_marker_icons[marker_title];
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

                // status_map_markers.push(marker); // Attach new marker to the map
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

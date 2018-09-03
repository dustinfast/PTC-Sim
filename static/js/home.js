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
var curr_loco = null;          // Selected loco. Ex: 'Loco 1001'
var curr_polylines = [];       // A list of all visible map polylines
var time_icand = 1             // Simulation speed multiplicand
var refresh_interval = 5000    // Async refresh interval
var on_interval = null;        // Ref to the active setInterval function
var persist_infobox = null;    // The map infobox to persist between refreshes


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
// Note: Can't seem to get JQuery shorthand working in ajax call (JSON trashed)
function updateContentAsync() {
    $.ajax({
        url: $SCRIPT_ROOT + '/_home_get_async_content',
        type: 'POST',
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify({ 'loco_name': curr_loco }),
        timeout: 1000,

        error: function (jqXHR, textStatus, errorThrown) {
            if (textStatus === 'timeout') {
                console.log('Content refresh timed out.');
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
                var marker_icon = data.status_map.markers[i].iconpath

                // Rotate loco icons according to heading. 
                if (marker_title.includes('Loco')) {
                    marker_icon = {
                        url: imgRotate(marker_icon, data.status_map.markers[i].rotation),
                        origin: new google.maps.Point(0, 0),  // image origin
                        anchor: new google.maps.Point(32, 0)  // from origin
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
                    // TODO: draggable: true, for helicoptering
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


// The setInterval handler. Returns a ref to the actual setInterval()
function setAsynchInterval (refresh_interval) {
        var setinterval = setInterval(function () {
            updateContentAsync();
    }, refresh_interval);

    // Update control panel refresh interval display
    // TODO: We're doing this in two places. Fix it.
    $('#refresh-val').html('&nbsp;' + refresh_interval / 1000 + 's');
    return setinterval;
}

// TODO:Call on main.html ready
function startHomeAsyncRefresh() {
    // Register slider onchange listeners and define their behavior
    var time_slider = $('#temporal-range')
    var refresh_slider = $('#refresh-range');
    time_disp = refresh_slider.val() + '%';
    refresh_disp = refresh_slider.val() + 's';

    time_slider.on('input', function () {
       new_val = $(this).val() / 100                // % to decimal
       main_set_sessionvar_async('time_icand', new_val);
        $('#time-icand').html('&nbsp;' + $(this).val() + '%');
    });
    refresh_slider.on('input', function () {
        new_val = $(this).val() * 1000              // s to ms
        clearInterval(on_interval);                 // Nullify current interval
        on_interval = setAsynchInterval(new_val);   // Start new setInterval
    });

    // Get the main content and update the page
    updateContentAsync();
    on_interval = setAsynchInterval(refresh_slider.val() * 1000) // s to ms
    $('#time-icand').html('&nbsp;' + time_slider.val() + '%');
    $('#refresh-val').html('&nbsp;' + refresh_slider.val() + 's');
}

// Rotates the image at the given url according to rotate_degree
function imgRotate(img_url, rotate_degrees ){
    var img = new Image();
    img.src = img_url;
    
    center_x = img.width / 2;
    center_y = img.height / 2;
    
    var canvas = document.createElement("canvas");
    canvas.width = img.width;
    canvas.height = img.height;

    var context = canvas.getContext("2d");
    context.clearRect(0, 0, img.width, img.height);
    context.save();                          // Push context state
    context.translate(center_x, center_y);
    context.rotate(rotate_degrees);
    context.translate(-center_x, -center_y);
    context.drawImage(img, 0, 0);
    context.restore();                      // Pop context state

    return canvas.toDataURL("image/png");
}

// function loadImage(url) {
//     return new Promise((resolve, reject) => {
//         let img = new Image();

//         // Listen for the image onload event (or its error event)
//         img.addEventListener('load', e => resolve(img));
//         img.addEventListener('error', () => {
//             reject(new Error(`Failed to load image's URL: ${url}`));
//         });

//         // Load the image, triggering the load (or error) events and
//         // fulfilling (or rejecting) the promise.
//         img.src = url;
//     });
// }

// loadImage(img_url)
//     .then((img, canvas) => {
//         center_x = img.width / 2;
//         center_y = img.height / 2;

//         var canvas = document.createElement("canvas");

//         canvas.width = img.width;
//         canvas.height = img.height;

//         context = canvas.getContext("2d");
//         context.clearRect(0, 0, img.width, img.height);
//         context.save();                          // Push context state
//         context.translate(center_x, center_y);
//         context.rotate(rotate_degrees);
//         context.translate(-center_x, -center_y);
//         context.drawImage(img, 0, 0);
//         context.restore();                      // Pop context state

//         console.log('Returning img url');
//         return canvas.toDataURL("image/png");
//     })
//     .catch(error => console.error('ERROR: ' + error));
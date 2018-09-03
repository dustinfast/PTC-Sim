// The top-level javascript library for PTC-Sim's web interface
// 
/// Author: Dustin Fast, 2018


// Sends a single key/value pair back to the server to update the corresponding
// server-side variable having the name given by the key.
function main_set_sessionvar_async(key, value) {
    $.ajax({
        url: $SCRIPT_ROOT + '/_set_sessionvar',
        type: 'POST',
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify({ key: key, value: value }),

        error: function (jqXHR, textStatus, errorThrown) {
            console.warn('Error contacting server for set var.');
        },

        success: function (data) {
            if (data == 'error') {
                console.warn('Server-server side error setting var')
                return;
            }
            // console.log('Set ' + key + ': ' + value) // debug
        }
    }
);}


// A Promise resolving with an Image after loading the image at image_url
function loadImage(image_url) {
    return new Promise((resolve, reject) => {
        let img = new Image();

        // Listen for the image onload event (or its error event)
        img.addEventListener('load', e => resolve(img));
        img.addEventListener('error', () => {
            reject(new Error(`Failed to load image's URL: ${image_url}`));
        });

        // Load the image, triggering the load (or error) event and thus
        // fulfilling (or rejecting) the promise.
        img.src = image_url;
    });
}
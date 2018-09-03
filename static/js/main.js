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

        success: function (data) {
            if (data == 'error') {
                console.error('Server returned error setting server-side var')
                return;
            }
            console.log('Set ' + key + ': ' + value) // debug
        }
    }
);}

// Accepts a js object and returns true iff obj is empty. For convenience.
function isObjEmpty(obj) {
    for (var k in obj) {
        if (obj.hasOwnProperty(k))
            return false;
    }
    return true;
}

function getFirst(obj) {
    for (var k in obj) {
        return obj[k];
    }
}
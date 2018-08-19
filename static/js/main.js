// Queries the server for updated home content json
function home_content_updater() {
    setInterval(function () {
        $.getJSON($SCRIPT_ROOT + "/_home_update",
            function (data) {
                $("#locos_table").text(data.locos_table);
                $("#loco_status").text(data.loco_status);
                // alert(data.locos_table);
            });
    }, 1000);
}

// function loco_selected() {

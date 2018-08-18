function update_content() {
    $.getJSON($SCRIPT_ROOT + "/_stuff",
              function (data) {
        $("loco_status").text(data.loco_status + " %")});
        // alert('test');
        }

function content_updater() {
    setInterval(function () {
        update_content();
    }, 10000);
}

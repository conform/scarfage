$(document).ready(function(){
    $('ul.nav-pills a').click(function (e) {
        $(this).tab('show');
        var scrollmem = $('body').scrollTop();
        window.location.hash = this.hash;
        $('html,body').scrollTop(scrollmem);
    });

    $('div.tab-content div').click(function (e) {
        $(this).tab('show');
        var scrollmem = $('body').scrollTop();
        window.location.hash = this.hash;
        $('html,body').scrollTop(scrollmem);
    });

    //Manage hash in URL to open the right pill
    var hash = window.location.hash;
    // If a hash is provided 
    if(hash && hash.length>0)
    {
        // Manage Pill titles
        $('ul.nav-pills li a').each(function( index ) {
            if($(this).attr('href')==hash)
                $(this).parent('li').addClass('active');
            else
                $(this).parent('li').removeClass('active');
        });

        // Manage Tab content
        var hash = hash.substring(1); // Remove the #
        $('div.tab-content div').each(function( index ) {
            if($(this).attr('id')==hash)
                $(this).addClass('fade in active');
            else
                $(this).removeClass('active');
        });
    }

    $('[data-toggle="tooltip"]').tooltip().click(function(e) {
        $(this).tooltip('hide');
    });

    $('.message-delete').click(function (e) {
        var dataid = $(this).attr('data-id');
        var user = $(this).attr('data-user');
        var success = function () { $('#message-' + dataid).remove(); };
        message_action(user, dataid, 'delete', success);
        return false;
    });
});

var url = document.location.href;

function message_action(user, messageid, action, success) {
    $.ajax({
      url: '/user/' + user + '/pm/' + messageid + '/' + action,
      type:"POST",
      contentType:"application/json; charset=utf-8",
      dataType:"json",
      success: success,
      error: function(XMLHttpRequest, textStatus, errorThrown) {
          //alert("Status: " + textStatus); alert("Error: " + errorThrown); 
      }
    })
}

new Clipboard('.copy-url', {
  text: function() {
    return url;
  }
});

// $() explanation https://stackoverflow.com/a/2167563/5288758

$(".list-unstyled").on("click", ".init", function() {
    $(this).closest("ul").children('li:not(.init)').toggle();
});

var allOptions = $(".list-unstyled").children('li:not(.init)');
$(".list-unstyled").on("click", "li:not(.init)", function() {
    allOptions.removeClass('selected');
    $(this).addClass('selected');
    $(".list-unstyled").children('.init').html($(this).html());
    allOptions.toggle();
});

function openDialog() {
    $('#overlay').fadeIn('fast', function() {
        $('#popup').css('display','block');
        $('#popup').animate({'left':'30%'},500);
    });
}

function closeDialog(id) {
    $('#'+id).css('position','absolute');
    $('#'+id).animate({'left':'-100%'}, 500, function() {
        $('#'+id).css('position','fixed');
        $('#'+id).css('left','100%');
        $('#overlay').fadeOut('fast');
    });
}
//轮播图
$('.right_btn').click(function () {
    var T = $('.right .slider .slider_box .ac').index();
    if (T < $('.right .slider .slider_box .slider_list').length - 1) {
        T = T;
    } else {
        T = -1;
    }
    $('.right .slider .slider_box .ac').animate({opacity: '0'}, 1000, function () {
        $(this).hide();
    });
    $('.right .slider .slider_box .ac').removeClass('ac');
    $('.right .slider .slider_box .slider_list').eq(T + 1).addClass('ac');
    $('.right .slider .slider_box .ac').show();
    $('.right .slider .slider_box .ac').animate({opacity: '1'}, 1000);
})
$('.left_btn').click(function () {
    var T = $('.right .slider .slider_box .ac').index();
    if (T > 0) {
        T = T;
    } else {
        T = $('.right .slider .slider_box .slider_list').length;
    }
    $('.right .slider .slider_box .ac').animate({opacity: '0'}, 1000, function () {
        $(this).hide();
    });
    $('.right .slider .slider_box .ac').removeClass('ac');
    $('.right .slider .slider_box .slider_list').eq(T - 1).addClass('ac');
    $('.right .slider .slider_box .ac').show();
    $('.right .slider .slider_box .ac').animate({opacity: '1'}, 1000);
})
setInterval(function () {
    var T = $('.right .slider .slider_box .ac').index();
    if (T < $('.right .slider .slider_box .slider_list').length - 1) {
        T = T;
    } else {
        T = -1;
    }
    $('.right .slider .slider_box .ac').animate({opacity: '0'}, 1000, function () {
        $(this).hide();
    });
    $('.right .slider .slider_box .ac').removeClass('ac');
    $('.right .slider .slider_box .slider_list').eq(T + 1).addClass('ac');
    $('.right .slider .slider_box .ac').show();
    $('.right .slider .slider_box .ac').animate({opacity: '1'}, 1000);
}, 6000)
//换图片
var W = $('.img_box li').width();
var W_1 = W + 14.5;
var T = $('.img_box li').length;
$('.img_box').width(W_1 * T);
$('.prev').click(function () {
    var now_Mf = $('.img_box').css('margin-left');
    var Mf = -parseInt(now_Mf) + W_1 * 7
    if (Mf > $('.img_box').width() - W_1 * 7) {
        $('.img_box').animate({'marginLeft': 0}, 300);
    } else {
        $('.img_box').animate({'marginLeft': -Mf}, 300);
    }
})
setInterval(function () {
    var now_Mf = $('.img_box').css('margin-left');    var Mf = -parseInt(now_Mf) - W_1 * 7;    console.log(Mf)    if (Mf < -0.5) {        Mf = $('.img_box').width() - W_1 * 7;        $('.img_box').animate({'marginLeft': -Mf}, 300);    } else {        $('.img_box').animate({'marginLeft': -Mf}, 300);    }
}, 6000)
$('.next').click(function () {
    var now_Mf = $('.img_box').css('margin-left');
    var Mf = -parseInt(now_Mf) - W_1 * 7;
    console.log(Mf)
    if (Mf < -0.5) {
        Mf = $('.img_box').width() - W_1 * 7;
        $('.img_box').animate({'marginLeft': -Mf}, 300);
    } else {
        $('.img_box').animate({'marginLeft': -Mf}, 300);
    }
})
//遮罩充满，文字全部显 示
/*$('.right .slider .slider_box .slider_list .text').mouseover(function(){
     $('.mask').stop().animate({height:'345px'},300);
     $(this).stop().animate({height:'345px'},400);
     $('.right .slider .slider_box .slider_list .text .p_5').stop().animate({height:'300px'},400);
});
$('.right .slider .slider_box .slider_list .text').mouseout(function(){
     $('.mask').stop().animate({height:'60px'},400);
     $(this).stop().animate({height:'60px'},300);
     $('.right .slider .slider_box .slider_list .text .p_5').stop().animate({height:'17px'},400);
}); */

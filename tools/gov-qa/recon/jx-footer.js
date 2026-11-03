$(document).ready(function () {
    // //国家部委网站
    // commonApi.getQueryList({
    //     current: 1,
    //     pageSize: 1,
    //     channelCode: ['gjbwwz'],
    //     webSiteCode: [websiteCode],
    // }, null, {
    //     listDom: '#footer-data-gjbwwz',
    //     createHtml: function (item) {
    //         return item.content.content
    //     },
    // })

    // //各省区市政府网站
    // commonApi.getQueryList({
    //     current: 1,
    //     pageSize: 1,
    //     channelCode: ['gsqszfwz'],
    //     webSiteCode: [websiteCode],
    // }, null, {
    //     listDom: '#footer-data-gsqszfwz',
    //     createHtml: function (item) {
    //         return item.content.content
    //     },
    // })
    // //各省区市政府网站
    // commonApi.getQueryList({
    //     current: 1,
    //     pageSize: 1,
    //     channelCode: ['szdwwz'],
    //     webSiteCode: [websiteCode],
    // }, null, {
    //     listDom: '#footer-data-szdwwz',
    //     createHtml: function (item) {
    //         return item.content.content
    //     },
    // })

    // // //省直单位网站
    // // commonApi.getQueryList({
    // //     current: 1,
    // //     pageSize: 12,
    // //     channelCode: ['szdwwz'],
    // //     webSiteCode: [websiteCode],
    // // }, null, {
    // //     listDom: '#footer-data-szdwwz',
    // //     createHtml: function (item) {
    // //         return '<div class="item-item mb10">\
    // //           <div class="com-title square mb15 none">\
    // //             <h3>' + item.title + '</h3>\
    // //           </div>\
    // //           ' + item.content.content + '\
    // //         </div>';
    // //     },
    // // })

    // //市县政府网站
    // commonApi.getQueryList({
    //     current: 1,
    //     pageSize: 12,
    //     channelCode: ['sxzfwz'],
    //     webSiteCode: [websiteCode],
    // }, null, {
    //     listDom: '#footer-data-sxzfwz',
    //     createHtml: function (item) {
    //         return '<div class="item-item mb20">\
    //           <div class="com-title square ' + (item.content ? 'mb15' : '') + '">\
    //             <h3><a href="' + item._url + '" target="_blank">' + item.title + '</a></h3>\
    //           </div>\
    //           ' + (item.content ? item.content.content : '') + '\
    //         </div>';
    //     },
    // })

    // //其他网站
    // commonApi.getQueryList({
    //     current: 1,
    //     pageSize: 1,
    //     channelCode: ['qtwz'],
    //     webSiteCode: [websiteCode],
    // }, null, {
    //     listDom: '#footer-data-qtwz',
    //     createHtml: function (item) {
    //         return item.content.content
    //     },
    // })

    //友情链接
    if ($('.footer-links').length > 0) {
        var $links = $('.footer-links .hd li.hs');
        $links.on('click', function (e) {
            var index = $links.index(this);
            $(this).toggleClass("on").siblings().removeClass("on");
            $(".footer-links .bd .item").eq(index).slideDown("fast").siblings().slideUp("fast");
            if (!$(this).hasClass('on')) {
                $(".footer-links .bd .item").eq(index).slideUp("fast");
            }
            e.preventDefault();
            e.stopPropagation();
        })
        $('body').on('click', function () {
            $links.removeClass("on");
            $(".footer-links .bd .item").slideUp("fast");
        })
    }

});
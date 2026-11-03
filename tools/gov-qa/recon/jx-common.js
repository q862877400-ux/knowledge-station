  
$(document).ready(function () {
    //头部导航选中效果
    mainnavSelectClass(window.channelsTagSelf);

    //添加面包屑
    commonApi.addCrumbs(window.channelsTagSelf, '#data-breadcrumbNav');

    //选项卡
    if ($(".js-tab").length > 0) {
        jQuery(".js-tab").slide({
            titCell: ".js-hd li:not('.islink')",
            mainCell: ".js-bd",
            delayTime: 0,
            triggerTime: 0,
            targetCell: ".more a"
        });
    }
    if ($(".js-tab-click").length > 0) {
        jQuery(".js-tab-click").slide({
            titCell: ".js-hd li:not('.islink')",
            mainCell: ".js-bd",
            trigger:"click",
            delayTime: 0,
            triggerTime: 0,
            targetCell: ".more a"
        });
    }


    //easybtn
    $(".quickbar dl").hover(function () {
        $(this).addClass('on')
        $(this).find("dd").show();
    }, function () {
        $(this).removeClass('on')
        $(this).find("dd").hide();
    })

    //返回顶部
    // 当网页向下滑动 200px 出现"返回顶部" 按钮
    window.onscroll = function () {
        scrollFunction()
    };
    $("#goTop a").click(function (e) {
        e.preventDefault();
        scrollToTop(500);
    })

    function scrollFunction() {
        if (document.body.scrollTop > 200 || document.documentElement.scrollTop > 200) {
            $("#goTop").slideDown("fast");
        } else {
            $("#goTop").slideUp("fast");
        }
    }

    function scrollToTop(time) {
        var time = time || 0;
        $("html,body").animate({
            scrollTop: 0
        }, time);
    }
    //域名弹窗白名单
    let SkipHosts=["www.jxsfzg.cn"]
    //非政府网站跳转提示: 点击外链询问离开
    //截取URL域名部份
    var getHost = function (url) {
        var host = "null";
        if (typeof url == "undefined" || null == url) url = window.location.href;
        var regex = /.*\:\/\/([^\/]*).*/;
        var match = url.match(regex);
        if (typeof match != "undefined" && null != match) host = match[1];
        return host;
    };
    //外链跳转弹框
    _outHtml = '<div class="alert-warning"><div class="alert-delete"><span id="closets">X</span></div><div class="alert-wzsm"><P>您即将访问非政府网站链接，是否继续？</P></div><div class="alert-footer"><span class="continue">继续访问</span><span class="fangqi">放弃</span></div></div><div class="alert-mengban"></div>', $("body").append(_outHtml);

    $(document).on('click', 'a', function (e) {
        if ($(this).hasClass('selflink')) return;
        var o = $(this),
            host, ckhost;
        var href = o.attr('href');
        if (href && !/^(?=javascript:)/.test(href) && /^(?=http)/.test(href)) {
            host = getHost(href);
            ckhost = host.indexOf('gov.cn');
        }
        if (href && host) {
            if (host != document.domain&&SkipHosts.indexOf(host)<0) {
                o.attr('target', '_blank');
                if (ckhost <= 0 && o.data('ask') != '1') {
                    $(".alert-mengban").fadeIn("fast");
                    $(".alert-warning").fadeIn("fast");
                    $("#closets,.fangqi, .alert-mengban").click(function () {
                        $(".alert-warning").fadeOut(300);
                        $(".alert-mengban").fadeOut(300);
                    });
                    $(".continue").one("click", function () {
                        $(".alert-warning").fadeOut(300);
                        $(".alert-mengban").fadeOut(200);
                        o.data('ask', '1');
                        o[0].click();
                        $("#closets").click();
                    });
                    return false;
                }
            }
        }
    });


    //埋点
    // 首页
    if (window.websiteId) {
        if (!window.channelId && !window.manuscriptId) {
            buryPoint({
                channelId: websiteId || undefined,
                channelName: $("meta[name='SiteName']").attr('content') || undefined,
            });
        }
    }
    // // 概览页
    if (window.channelId && !window.manuscriptId) {
        buryPoint({
            channelId: channelId || undefined,
            channelName: $("meta[name='ColumnName']").attr('content') || undefined,
        });
    }
    // // 细览页
    if (window.manuscriptId) {
        buryPoint({
            channelId: channelId || undefined,
            channelName: $("meta[name='ColumnName']").attr('content') || undefined,
            title: $("meta[name='ArticleTitle']").attr('content') || undefined,
            articleId: manuscriptId || undefined,
            pubDate: $("meta[name='PubDate']").attr('content') || undefined,
            url: window.location.href || '',
        });
    }

});

//头部导航选中效果
function mainnavSelectClass(data) {
    if (!data || $('#data-mainnav').length == 0) return;
    if (data.crumbs && data.crumbs.length) {
        var rootName = data.crumbs[0].name;
        $("#data-mainnav li").each(function () {
            if ($.trim($(this).find("a").attr('title')) == rootName) {
                $(this).addClass("on").siblings().removeClass('on');
            }
        })

    }
}

//去掉所有的html标记
function delHtmlTag(str) {
  return str.replace(/<[^>]+>/g, ""); //去掉所有的html标记
}


// // 记录埋点的请求
function buryPoint(params) {
    var buryPointUrl = '/saveAccessLog' // 埋点请求地址
    var postData = {
        siteId: websiteId || defaultConfig.userIdObj.siteId,
        deptId: defaultConfig.userIdObj.deptId,
        tenantId: defaultConfig.userIdObj.tenantId,
        siteName: $("meta[name='SiteName']").attr('content') || undefined,
        channelId: params && params.channelId || undefined,
        channelName: params && params.channelName || undefined,
        title: params && params.title || undefined,
        articleId: params && params.articleId || undefined,
        pubDate:  params && params.pubDate || undefined,
        url: window.location.href || '',
    }
    // console.log('buryPoint-postData', postData);
    $.ajax({
        url: buryPointUrl,
        type: 'post',
        data: postData,
        dataType: 'json',
        success: function () {},
        error: function () {}
    })
}
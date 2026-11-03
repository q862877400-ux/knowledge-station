/* 页面交互公共效果 */

// 工具方法(针对前后端分离,如不是需删除)
(function (win, $) {
    $('#key').val('');
    if (!window.suUtil) {
        window.suUtil = {};
    }
    /*
     * 序列化表单元素，区别于jQuery 的serialize和serializeArray方法
     */
    $.fn.serializeObject = function () {
        var o = {};
        var a = this.serializeArray();
        $.each(a, function () {
            if (o[this.name]) {
                if (!o[this.name].push) {
                    o[this.name] = [o[this.name]];
                }
                o[this.name].push(this.value || '');
            } else {
                o[this.name] = this.value || '';
            }
        });
        return o;
    };
    $.extend(suUtil, {
        /* 获取URL地址参数
         * prop:参数名
         */
        getUrlParams: function (prop) {
            var params = {},
                query = location.search.substring(1),
                arr = query.split('&'),
                rt;

            $.each(arr, function (i, item) {
                var tmp = item.split('='),
                    key = tmp[0],
                    val = tmp[1];

                if (typeof params[key] == 'undefined') {
                    params[key] = val;
                } else if (typeof params[key] == 'string') {
                    params[key] = [params[key], val];
                } else {
                    params[key].push(val);
                }
            });
            rt = prop ? params[prop] : params;
            return rt;
        },

        // 适配f9中的response格式
        ajax: function (options) {
            options = $.extend(
                {},
                {
                    type: 'POST',
                    dataType: 'json',
                    dataFilter: function (data, type) {
                        if (type == 'json') {
                            data = JSON.parse(data);

                            // TODO: 这里可以对data做些统一处理，权限处理等

                            data = data.UserArea;

                            if (typeof data == 'object') {
                                data = JSON.stringify(data);
                            }
                        }

                        return data;
                    },
                    error: suUtil._ajaxErr
                },
                options
            );

            //options.url = SrcBoot.getPath(options.url);

            return $.ajax(options);
        },

        // 动态加载js
        loadJs: function (url, callback) {
            var script = document.createElement('script');
            script.type = 'text/javascript';

            // IE8-
            if (callback) {
                if (script.readyState) {
                    script.onreadystatechange = function () {
                        if (script.readyState == 'loaded' || script.readyState == 'complete') {
                            script.onreadystatechange = null;
                            callback();
                        }
                    };
                    // w3c
                } else {
                    script.onload = function () {
                        callback();
                        script.onload = null;
                    };
                }
            }

            script.src = url;
            // append to head
            document.getElementsByTagName('body')[0].appendChild(script);
        },

        // 动态加载css
        loadCss: function (url) {
            var $link = $('<link/>', {
                type: 'text/css',
                rel: 'stylesheet',
                href: url
            });

            $link.appendTo(document.getElementsByTagName('head')[0]);
        },

        // empty function
        noop: function () {},

        // 去除html标签中的换行符和空格
        clearHtml: function (html) {
            return html
                .replace(/(\r\n|\n|\r)/g, '')
                .replace(/[\t ]+\</g, '<')
                .replace(/\>[\t ]+\</g, '><')
                .replace(/\>[\t ]+$/g, '>');
        }

        //      _ajaxErr: function(jqXHR, textStatus, errorThrown) {
        //          console.error('status: %s, error: %s', textStatus, errorThrown);
        //      }
    });

    /*
     * 动态加载CSSJS使用示例
     */
    //  Util.loadCss("css/grid.20.980.css");
    //  Util.loadJs('js/lib/jquery.cookie.js', function() {
    //      console.log("回调函数");
    //  });
})(this, jQuery);

// 加载头尾代码片段
(function (win, $) {
    win.Include = function (cfg) {
        this.cfg = cfg;

        this._init();
    };

    Include.prototype = {
        constructor: Include,

        _init: function () {
            var c = this.cfg;

            if (c.async !== false) c.async = true;

            this.$container = $('#' + c.id);
        },

        fetch: function () {
            var c = this.cfg,
                self = this;

            return $.ajax({
                url: c.src,
                type: 'GET',
                dataType: 'html',
                async: c.async,
                success: function (html) {
                    self.$container.html(html);

                    c.onload && c.onload(html);
                }
            });
        }
    };

    // 需要引入的代码片段 ★头尾是js加载的，头尾的js要写在回调函数里★
    var includes = [
        {
            id: 'header',
            src: 'header.inc.html',
            onload: function () {
                win.inputTips.init();
            }
        },
        {
            id: 'speheader',
            src: '/speheader.inc.html',
            onload: function () {
                win.inputTips.init();
            }
        },
        {
            id: 'footer',
            src: '/footer.inc.html',
            onload: function () {
                // console.log('...footer loaded...');
            }
        },
        {
            id: 'subheader',
            src: '/subheader.inc.html',
            onload: function () {
                //导航栏交互
                var locationurl = window.location.href;
                //console.log(locationurl);
                if (locationurl.indexOf('zxzx') != -1) {
                    $('#zxzx').addClass('current');
                    $('#zwgk').removeClass('current');
                    $('#hdjl').removeClass('current');
                    $('#zqdh').removeClass('current');
                }
                if (locationurl.indexOf('zwgk') != -1) {
                    $('#zwgk').addClass('current');
                    $('#zxzx').removeClass('current');
                    $('#hdjl').removeClass('current');
                    $('#zqdh').removeClass('current');
                }
                if (locationurl.indexOf('hdjl') != -1) {
                    $('#zxzx').removeClass('current');
                    $('#zwgk').removeClass('current');
                    $('#hdjl').addClass('current');
                    $('#zqdh').removeClass('current');
                }
                if (locationurl.indexOf('zqdh') != -1) {
                    $('#zxzx').removeClass('current');
                    $('#zwgk').removeClass('current');
                    $('#hdjl').removeClass('current');
                    $('#zqdh').addClass('current');
                }

                if (locationurl.indexOf('zqdh') != -1) {
                    $('#zxzx').removeClass('current');
                    $('#zwgk').removeClass('current');
                    $('#hdjl').removeClass('current');
                    $('#zqdh').addClass('current');
                }

                if (locationurl.indexOf('zqdh') != -1) {
                    $('#zxzx').removeClass('current');
                    $('#zwgk').removeClass('current');
                    $('#hdjl').removeClass('current');
                    $('#zqdh').addClass('current');
                }

                if (locationurl.indexOf('zqdh') != -1) {
                    $('#zxzx').removeClass('current');
                    $('#zwgk').removeClass('current');
                    $('#hdjl').removeClass('current');
                    $('#zqdh').addClass('current');
                }

                if (locationurl.indexOf('zqdh') != -1) {
                    $('#zxzx').removeClass('current');
                    $('#zwgk').removeClass('current');
                    $('#hdjl').removeClass('current');
                    $('#zqdh').addClass('current');
                }

                $('#searchBtn').on('click', function () {
                    var searchCon = $('#key').val();
                    if (searchCon == '' || searchCon == undefined || $.trim(searchCon) == '') {
                        alert('请输入您要搜索的关键字！！');
                    } else {
                        var pattern = new RegExp(
                            "[%!@#$^*()=|{}':;',\\[\\].<>/~！@#￥……*（）;—|{}【】‘；：”“'。，、&]"
                        );

                        window.open('/fullsearch.html?wd=' + searchCon.trim());
                    }
                });
                //回车键搜索
                $('#key').bind('keydown', function (event) {
                    var event = window.event || arguments.callee.caller.arguments[0];
                    if (event.keyCode == 13) {
                        var searchCon = $('#key').val();
                        if (searchCon == '' || searchCon == undefined || $.trim(searchCon) == '') {
                            alert('请输入您要搜索的关键字！！');
                        } else {
                            var pattern = new RegExp(
                                "[%!@#$^*()=|{}':;',\\[\\].<>/~！@#￥……*（）;—|{}【】‘；：”“'。，、&]"
                            );

                            window.open('/fullsearch.html?wd=' + searchCon.trim());
                        }
                    }
                });
                win.inputTips.init();
                // 侧边推移菜单
                var $mobileTrigger = $('#mobile-trigger');
                $mobileTrigger.sidr({
                    timing: 'ease-in-out',
                    speed: 500,
                    // side: 'right',  //显示在右侧
                    source: '#mob-menu',
                    bind: 'click',
                    renaming: false,
                    name: 'mob-menu'
                });

                // 2022-4-26新增
                var $mobMenu = $('#mob-menu'),
                    $ewbNav = $('.ewb-nav');

                if ($(window).width() > 768) {
                    $mobMenu.css('display', 'none');
                } else {
                    $ewbNav.css('display', 'none');
                    $('.hidden-phone').addClass('yx_not');
                    $('.wb-tree').addClass('yx_not');
                }
                // 2022-4-26新增
            }
        },
        {
            id: 'subfooter',
            src: '/subfooter.inc.html',
            onload: function () {
                function IsPC() {
                    var userAgentInfo = navigator.userAgent;
                    var Agents = ['Android', 'iPhone', 'SymbianOS', 'Windows Phone', 'iPad', 'iPod'];
                    var flag = true;
                    for (var v = 0; v < Agents.length; v++) {
                        if (userAgentInfo.indexOf(Agents[v]) > 0) {
                            flag = false;
                            break;
                        }
                    }
                    return flag;
                }
                if (IsPC()) {
                    $('.foot-para br').remove();
                }
            }
        }
    ];

    $.each(includes, function (i, cfg) {
        if ($('#' + cfg.id).length) {
            new Include(cfg).fetch();
        }
    });


})(this, jQuery);

/* 其他公用js */

(function (win, $) {
    // IE8 body处理
    if (document.all && !document.addEventListener) {
        //1200px 为container尺寸，视具体设计稿而定
        $('body').css('min-width', '1100px');
    }
    // placeholder
    win.inputTips = new inputPlaceholder();

    // 2022-3-10新增
    var $uncommon = $('.uncommon');
    $uncommon.each(function () {
        var $this = $(this);
        var temp = '<span class="uncommon-box"><span>' + $this.data('uncommon') + '</span></span>';
        $this.append(temp);
    });

    $("body").on("click","a",function(){
    
    	var thisa = $(this);
    	var url = thisa.attr('href');
    	//判断是否是适老化模式
    	var toolbarState=toolbar.cookie.getCookie('toolbarState');
    	if (url&&toolbarState=="1"){
    			var urltrim = $.trim(url).toLowerCase();
    			if((urltrim.indexOf("http://") == 0 || urltrim.indexOf("https://") == 0)) {
    				var urltext = thisa.text();
    				if($.trim(urltext) == ""){
    					urltext = thisa.attr("alt");
    				}
    				if(urltext==undefined){
    					layer.confirm('您即将进入新窗口页面，请确认', {
    						title: '友情提示',
    						btn: ['是','否'],
    						btn1:function(){
    							layer.closeAll();
    							window.open(url, "_blank");
    						}, 
    						btn2:function(){
    							layer.closeAll();
    						}
    					});
    				}else{
    					layer.confirm('您即将进入“'+urltext+'”新窗口页面，请确认', {
    						title: '友情提示',
    						btn: ['是','否'],
    						btn1:function(){
    							layer.closeAll();
    							window.open(url, "_blank");
    						}, 
    						btn2:function(){
    							layer.closeAll();
    						}
    					});
    				}
    				return false;
    			}
    		}
    });


})(this, jQuery);

function baiduSpeakgxh(text) {
    //var text = $(".langdu").text();
    $.ajax({
        url: toolbar.config.baiduaddress,
        type: 'post',
        data: {},
        dataType: 'json',
        success: function (msg) {
            soundManager.setup({
                url: '/js/ABT/swf/',
                onready: function () {
                    var speed = '5';

                    stopSpeak();
                    var soundurl =
                        'http://tsn.baidu.com/text2audio?lan=zh&ctp=1&cuid=1&tok=' +
                        $.parseJSON(msg.custom.result).access_token +
                        '&tex="' +
                        encodeURI(text) +
                        '&vol=9&spd=' +
                        speed;
                    var mySound = soundManager.createSound({
                        id: new Date().getTime(),
                        url: soundurl,
                        onfinish: function () {
                            // once sound has loaded and played, unload and destroy it.
                            this.destruct(); // will also try to unload before destroying.
                            soundManager.stopAll();
                        }
                    });
                    mySound.play({
                        onfinish: function () {
                            $('.readload1').removeClass('active');
                        }
                    });
                }
            });
        },
        error: function (msg) {
            //console.log(msg);
        }
    });
}

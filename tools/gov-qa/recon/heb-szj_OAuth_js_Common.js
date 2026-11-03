//针对OAuth2.0 对ajax进行了封装

(function($) {
    // 默认错误提示文本
    var ERROR_MSG = {
        400: '不合法的请求或被安全拦截。',
        401: '未授权或未登录。',
        403: '对资源没有访问权限。',
        404: '请求的资源无法找到。',
        500: '服务器内部错误。',
        503: '服务器正忙，请稍后再试。',
        timeout: '服务器正忙，请稍后再试。',
        parsererror: '数据解析异常，返回 JSON 格式不合法。'
    };

    // 获取url参数值
    var getUrlParams = function(name) {
        var params = {}, query = location.search.substring(1), arr = query.split('&'), rt;

        $.each(arr, function(i, item) {
            var tmp = item.split('='),
                key = tmp[0],
                val = decodeURIComponent(tmp[1]);
            if (typeof params[key] == 'undefined') {
                params[key] = val;
            } else if (typeof params[key] == 'string') {
                params[key] = [params[key], val];
            } else {
                params[key].push(val);
            }
        });
        rt = name ? params[name] : params;
        return rt;
    };

    //删除URL指定参数
    var delUrlParam = function(ref) {
        if (location.href.indexOf("?") == -1) {
            return location.href;
        }
        var base = location.href.split("?")[0];
        if (typeof ref == "string") {
            ref = [ref];
        }
        var params = getUrlParams();
        $.each(ref, function(i, r) {
            if (params[r]) {
                delete params[r];
            }
        });
        var params_str = $.param(params);
        if (params_str.length > 0) {
            base += "?";
        }
        return base + params_str;
    };


    // 获取错误回调
    // needTip: 是否需要提示
    // logLevel: console级别
    var getErrHandler = function(needTip, logLevel) {

        return function(xhr) {
            var errMsg = xhr.responseJSON && xhr.responseJSON.error,
                debugMsg = ['请求地址：', this.url, ', 状态码：' + (xhr.status || '超时'), ', 错误信息：', errMsg || ERROR_MSG[xhr.status]].join('');

            if (needTip) Util.showAjaxErr(errMsg || debugMsg);

            //console[logLevel || 'error'](debugMsg);
        };
    };
    if (!window.Util) {
        window.Util = {};
    }
    $.extend(Util, {
        // 按照最新传参标准的默认实现
        ajaxParamsHandler: function(data) {
            if (!data) {
                return undefined;
            } else {
            	if (data.params && (typeof data.params === "object" || typeof data.params === "string")) {
                    return data;
                } else {
                    return {
                        params: JSON.stringify(data)
                    }
                }
            }
        },
        //对$.ajax进行OAuth封装，options参数和$.ajax一直，isAnonymous：是否匿名访问
        ajax: function(options, isAnonymous) {
            options = $.extend({}, {
                type: 'post',
                dataType: 'json'
            }, options);

            var success = function() { }, error = function() { };

            if ($.isFunction(options.success)) {
                success = options.success;

                options.success = null;
                delete options.success;
            }
            if ($.isFunction(options.error)) {
                error = options.error;

                options.error = null;
                delete options.error;
            }
            options.data = $.proxy(Util.ajaxParamsHandler, this)(options.data);


            var xhr1, xhr2, xhr3;
            var dtd = $.Deferred();

            //判断是否初始化
            if (!OAuthInstance.isInit()) {
                xhr1 = OAuthInstance.initApp();
            } else {
                xhr1 = dtd.promise();
            }

            //判断是否有匿名token
            if (!OAuthInstance.anonymousToken()) {
                xhr2 = OAuthInstance.getAnonymousToken();
            } else {
                xhr2 = dtd.promise();
            }

            //如果存在code参数，说明是登陆后跳转到该地址
            var code = getUrlParams("code");
            if (code) {
                xhr3 = OAuthInstance.getToken(code, window.location.href);
            } else {
                xhr3 = dtd.promise();
            }

            var tokenAjax = xhr1.then(function() {
                return xhr3.then(function() {
                    if (!isAnonymous && !OAuthInstance.isLogin()) {
                        if (layer) {
							layer.open({
								title: '温馨提示',
								content: '您还未登录，点击确认去登录^_^',
								closeBtn: 0,
								yes: function(index, layero){
									OAuthInstance.goLogin();
									layer.close(index);
								}
							}); 
						} else {
							if (confirm("您还未登录，点击确认去登录")) { 
								OAuthInstance.goLogin();
							}
						}
                        return;
                    }
                    else {
                        return xhr2.then(function() {
                            var url = location.href;
                            var newurl = delUrlParam(["code", "state", "timestamp"]);
                            if (url != newurl) {
                                window.location.replace(newurl);
								return;
                            }

                            var isAnonymousToken = true;
                            if (OAuthInstance.accessToken()) {
                                isAnonymousToken = false;
                            }

                            if (isAnonymous) {
                                options.beforeSend = function(xhr) {
                                    var accessToken = OAuthInstance.accessToken() || OAuthInstance.anonymousToken();
                                    xhr.setRequestHeader("Authorization", "Bearer " + accessToken);
                                };
                            } else {
                                options.beforeSend = function(xhr) {
                                    xhr.setRequestHeader("Authorization", "Bearer " + OAuthInstance.accessToken());
                                };
                            }

                            var xhr = $.ajax(options);
                            return xhr.then(Util.ajaxPreSuccess, function(xhr, textStatus, errorThrown) {
                                if (xhr.status == 403||xhr.status == 404) {
                                    options.success = success;
                                    options.error = error;
                                    var tmpRefreshTokenXhr;
                                    if (isAnonymousToken) {
                                        tmpRefreshTokenXhr = OAuthInstance.refreshAnonymousToken();
                                    } else {
                                        tmpRefreshTokenXhr = OAuthInstance.refreshToken();
                                    };
                                    return tmpRefreshTokenXhr.then(function() {
                                        return Util.ajax(options, isAnonymous);
                                    }, function(xhr, textStatus, errorThrown) {
                                        Util.ajaxError(xhr, textStatus, errorThrown);
                                        error(xhr, textStatus, errorThrown);
                                    });

                                } else {
                                    Util.ajaxError(xhr, textStatus, errorThrown);
                                    error(xhr, textStatus, errorThrown);
                                }

                            }).done(success);
                        });
                    }
                });
            });
            dtd.resolve();
            return tokenAjax;
        },
        
        // 去除html标签中的换行符和空格
        clearHtml: function(html) {
            return html.replace(/(\r\n|\n|\r)/g, "")
                .replace(/[\t ]+\</g, "<")
                .replace(/\>[\t ]+\</g, "><")
                .replace(/\>[\t ]+$/g, ">");
        },


        // 主要用于针对 status 节点进行一些通用的预处理，可以进行重写
        statusNodeHandler: function(code, text, url) {
            if (code !== 1 || code !== 200) {
                if (text) {
                    //alert(text);
                }
            }
        },

        ajaxPreSuccess: function(data) {
            var status = data.status,
                code = 1, text = '', url = '';

            // f9 response
            if (status) {
                code = status.code - 0; text = status.text; url = status.url;
                $.proxy(Util.statusNodeHandler, this)(code, text, url);
            }

            return data;
        },

        showAjaxErr: function(msg) {
            alert(msg);
        },

        // 跟进响应码，进行响应异常的处理
        responseErrHandlers: {
            // 安全拦截
            400: getErrHandler(1),
            // 未登录，一般弹出快速登录框
            401: function(xhr) {
                $.proxy(getErrHandler(0, 'info'), this)(xhr);
            },
            // 无权限
            403: getErrHandler(1),
            // 找不到资源
            404: getErrHandler(1),
            // 后台报错
            500: getErrHandler(1),
            // 后台暂时不可用
            503: getErrHandler(1),
            // 响应超时
            timeout: getErrHandler(1),
            // 响应格式解析异常
            parsererror: function(xhr) {
                //console.error('request: %s, response: %s, error: %s', this.url, xhr.responseText, ERROR_MSG.parsererror);
            },
            // 其他响应异常处理
            other: function(xhr, statusText, errorThrown) {
                //console.error('request: %s, status: %s, error: %s', this.url, xhr.status, errorThrown);
            }
        },

        // 对请求错误进行通用处理
        ajaxError: function(xhr, textStatus, errorThrown) {
            var callback = function() { };

            if (textStatus === 'timeout' || textStatus === 'parsererror') {
                callback = Util.responseErrHandlers[textStatus];

            } else if ($.inArray(xhr.status, [400, 401, 403, 404, 500, 503]) > -1) {
                callback = Util.responseErrHandlers[xhr.status];

            } else {
                callback = Util.responseErrHandlers.other;
            }

            $.proxy(callback, this)(xhr, textStatus, errorThrown);
        }
    });
})($);

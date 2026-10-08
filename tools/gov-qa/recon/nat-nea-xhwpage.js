"use strict";

// window.onload = function () {
// 引入分页插件

var jqPaginator = document.createElement('script');
jqPaginator.type = "text/javascript";
jqPaginator.src = 'https://www.nea.gov.cn/2025nyj/xinban/tyej_js/jq-paginator.min.js';

$('head').append(jqPaginator);

function ownKeys(object, enumerableOnly) {
    var keys = Object.keys(object);
    if (Object.getOwnPropertySymbols) {
        var symbols = Object.getOwnPropertySymbols(object);
        if (enumerableOnly) {
            symbols = symbols.filter(function (sym) {
                return Object.getOwnPropertyDescriptor(object, sym).enumerable;
            });
        }
        keys.push.apply(keys, symbols);
    }
    return keys;
}

function _objectSpread(target) {
    for (var i = 1; i < arguments.length; i++) {
        var source = arguments[i] != null ? arguments[i] : {};
        if (i % 2) {
            ownKeys(Object(source), true).forEach(function (key) {
                _defineProperty(target, key, source[key]);
            });
        } else if (Object.getOwnPropertyDescriptors) {
            Object.defineProperties(target, Object.getOwnPropertyDescriptors(source));
        } else {
            ownKeys(Object(source)).forEach(function (key) {
                Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key));
            });
        }
    }
    return target;
}

function _defineProperty(obj, key, value) {
    if (key in obj) {
        Object.defineProperty(obj, key, {
            value: value,
            enumerable: true,
            configurable: true,
            writable: true
        });
    } else {
        obj[key] = value;
    }
    return obj;
}

function _classCallCheck(instance, Constructor) {
    if (!(instance instanceof Constructor)) {
        throw new TypeError("Cannot call a class as a function");
    }
}

function _defineProperties(target, props) {
    for (var i = 0; i < props.length; i++) {
        var descriptor = props[i];
        descriptor.enumerable = descriptor.enumerable || false;
        descriptor.configurable = true;
        if ("value" in descriptor) descriptor.writable = true;
        Object.defineProperty(target, descriptor.key, descriptor);
    }
}

function _createClass(Constructor, protoProps, staticProps) {
    if (protoProps) _defineProperties(Constructor.prototype, protoProps);
    if (staticProps) _defineProperties(Constructor, staticProps);
    return Constructor;
}

/**
 * 参数
 * parentNode 组件元素名称
 * itemNode 加载数据父级元素名称
 * btn 加载按钮元素名称
 * type 类型 more加载更多 page 分页
 * isLoading more类型使用 加载中
 * isHasMore more类型使用 查看更多
 * isEmpty more类型使用 暂无数据
 * isError more类型使用 加载失败，请重试
 * isNoMore more类型使用 暂无更多
 * startSize 初始条数
 * pageNum 页码
 * pagesize 条数
 * datasource 数据源id
 * url 数据请求地址
 * 
 * 以下只针对type=== page有用
 * preText   上一页 文字
 * nextText 下一页 文字
 * homeText 首页 文字
 * endText 尾页 文字
 * showPagerSize 显示 页码数量 
 */
var Xhwpage = /*#__PURE__*/function () {
    function Xhwpage(options) {
        _classCallCheck(this, Xhwpage);

        this.options = _objectSpread({
            type: "more",
            parentNode: ".xhwPage",
            itemNode: "",
            btn: ".moreBtn",
            isLoading: "加载中...",
            isHasMore: "查看更多",
            isEmpty: "暂无数据",
            isError: "加载失败，请重试",
            isNoMore: "暂无更多",
            url: "",
            pageNum: 1,
            pageSize: 10,
            startSize: "",
            preText: '上一页',
            nextText: '下一页',
            homeText: '首页',
            endText: '尾页',
            showPagerSize: 5,
            template: '\n            <li class="list-item" v-for=\'(item,index) in datasource.datasource\' :key=\'index\' v-if=\'index < 10\'>\n              <a :href="item.publishUrl" target="_blank">\n                  <img :src="item.titleImages[0].imageUrl">\n              </a>\n              <div class="listright">\n                  <a :href="item.publishUrl" class="tit" target="_blank">{{item.showTitle}}</a>\n                  <span>{{item.publishTime}}</span>\n              </div>\n          </li>',
            //数据加载前的操作
            beforeMount: function beforeMount() {},
            //数据加载完成操作
            updated: function updated() {}
        }, options);
        this.filters = _objectSpread({
            subTime: function subTime(value, arg) {
                return value ? value.substr(0, arg) : "";
            },
            year: function year(value) {
                return value ? value.substring(0, 4) : "";
            },
            month: function month(value) {
                return value ? value.substring(5, 7) : "";
            },
            day: function day(value) {
                return value ? value.substring(8, 10) : "";
            },
            time: function time(value) {
                return value ? value.substr(11) : "";
            },
            hour: function hour(value) {
                return value ? value.substring(11, 13) : "";
            },
            minute: function minute(value) {
                return value ? value.substring(14, 16) : "";
            },
            second: function second(value) {
                return value ? value.substring(17) : "";
            },
            filterLinkLabel: function filterLinkLabel(value, type) {
                // console.log(value);

                if (!value || type && type === "html") {
                    return value;
                }

                var div = document.createElement("div");
                div.innerHTML = value;
                value = div.innerText;
                return value;
            }
        }, this.options.filters);
        if (this.options.type === 'page') {
            var url = this.extractUrl
            // 创建style 标签
            ();var parentBtnBox = this.options.btn;
            // 定义选中 以及 基本样式
            var cssStyle = "\n      " + parentBtnBox + " span.active {\n        background-color: #348CEC !important;\n        color: #fff !important;\n      }\n      " + parentBtnBox + " span.spanPagerStyle {\n        display: inline-block;\n        padding: 0 10px;\n        height: 26px;\n        font-size: 12px;\n        color: #818181;\n        text-align: center;\n        line-height: 26px;\n        background-color: #F1F3F5;\n        margin: 0 3px;\n        cursor: pointer\n      }\n      ";
            var styleTag = document.createElement('style');

            $('head').append(styleTag);
            styleTag.type = 'text/css';
            if (styleTag.styleSheet) {
                styleTag.styleSheet.cssText = cssStyle;
            } else {
                styleTag.appendChild(document.createTextNode(cssStyle));
            }
            var that = this;
            setTimeout(function () {
                $(that.options.parentNode).html(that.options.template);
                var template = $(that.options.parentNode)[0].outerHTML;
                new Vue({
                    el: that.options.parentNode,
                    data: function data() {
                        return {
                            datasource: {
                                datasource: []
                            }
                        };
                    },
                    mounted: function mounted() {
                        this.getDatasourceJsonFn();
                    },

                    methods: {
                        getDatasourceJsonFn: function getDatasourceJsonFn() {
                            var _this5 = this;

                            $.ajax({
                                url: url,
                                type: "GET",
                                dataType: "json"
                            }).then(function (res) {
                                if (res && res.datasource) {
                                    var datasource = res.datasource;
                                    var datasourceLen = res.datasource.length;
                                    var size = that.options.pageSize || 10;
                                    var showPagerSize = that.options.showPagerSize || 5;

                                    var pagesNum = Math.ceil(datasourceLen / size
                                    // 创建 分页盒子
                                    );var pagerSpan = document.createElement('span');
                                    pagerSpan.className = 'pagerSpanClass';
                                    var preText = that.options.preText || '上一页';
                                    var nextText = that.options.nextText || '下一页';
                                    var homeText = that.options.homeText || '首页';
                                    var endText = that.options.endText || '尾页';
                                    // this.disposePagerLogic(1, parentBtnBox, datasource, pagesNum, size)
                                    $(parentBtnBox).jqPaginator({
                                        totalPages: pagesNum,
                                        visiblePages: showPagerSize,
                                        currentPage: 1,
                                        first: "<span class=\"homeClass spanPagerStyle\">" + homeText + "</span>",
                                        last: "<span class=\"endClass spanPagerStyle\">" + endText + "</span>",
                                        prev: "<span class=\"prevClass spanPagerStyle\">" + preText + "</span>",
                                        next: "<span class=\"nextClass spanPagerStyle\">" + nextText + "</span>",
                                        page: "<span class=\"page spanPagerStyle\">{{page}}</span>",
                                        onPageChange: function onPageChange(num, type) {
                                            _this5.disposePagerLogic(num, parentBtnBox, datasource, pagesNum, size);
                                        }
                                    });
                                }
                            });
                        },
                        disposePagerLogic: function disposePagerLogic(targetValue, parentBtnBox, datasource, pagesNum, size) {
                            // 根据展示页码 进行 首页上一页下一页按钮的显示切换
                            var beforeShow = targetValue <= 1 ? 'none' : 'inline-block';
                            var afterShow = targetValue >= pagesNum ? 'none' : 'inline-block';
                            // 异步否则获取不到dom
                            setTimeout(function () {
                                $(parentBtnBox + " .homeClass").css('display', beforeShow);
                                $(parentBtnBox + " .prevClass").css('display', beforeShow);
                                $(parentBtnBox + " .nextClass").css('display', afterShow);
                                $(parentBtnBox + " .endClass").css('display', afterShow);
                            }, 0);

                            var start = (targetValue - 1) * size;
                            var end = targetValue * size;
                            // 当前页码对应数据
                            var sliceData = datasource.slice(start, end);
                            this.datasource.datasource = sliceData;
                        }
                    },
                    updated: function updated() {
                        // console.log(0)
                        // console.log(that.options.template)
                    },

                    filters: _objectSpread({}, that.filters),
                    // filters: that.filters,
                    // $(that.options.parentNode).text(that.options.template)
                    // 拼接 template
                    template: template
                });
            });

            return;
        }

        this.itemNode = this.options.itemNode || this.findLableName(this.options.template); // 加载更多元素按钮

        this.btn = $(this.options.btn);
        this.app = [];
        this.type = this.options.type; //重新设置页码，必须为数字类型

        this.pageNum = parseInt(this.options.pageNum);

        if (this.btn.length == 0) {
            return;
        }

        this.location = window.location.host;
        this.pathname = window.location.pathname;
        this.vUrl = "http://bucket-cb-yunqiao.oss-cn-beijing-xhcloud-d01-a.xhcloud.news.cn/publish/pseudo-data/ds_0f04287970834daf8cfb5b203e8f3bac.json";
        this.eventEmmit();
    }

    _createClass(Xhwpage, [{
        key: "eventEmmit",
        value: function eventEmmit() {
            var _this2 = this;

            this.btn.each(function (i, e) {
                var rand = _this2.randomWord(false, 15);

                var id = "x" + rand;
                var vueId = "v" + rand;
                var dom = $(e); // 获取当前组件元素
                var component = $(_this2.options.parentNode);
                var url = _this2.extractUrl();

                dom.attr("vueId", vueId);
                $("body").append("<div id='".concat(id, "'></div>"));
                var _this = _this2;
                e.addEventListener("click", function () {
                    if (_this2.type === "more") {
                        var hasDisabled = dom.attr("disabled");

                        if (hasDisabled === "disabled") {
                            return;
                        } //设置加载中

                        dom.text(_this2.options.isLoading).attr("disabled", "disabled");
                    } else {
                        dom.addClass("active").siblings().removeClass("active");
                    }

                    var pageNum = _this2.type === "more" ? _this2.pageNum += 1 : _this2.pageNum;
                    var startPage = _this2.options.startSize ? _this2.options.startSize + (pageNum - 2) * _this2.options.pageSize : (pageNum - 1) * _this2.options.pageSize; //获取当前总页数

                    var endPage = _this2.options.startSize ? _this2.options.startSize + (pageNum - 1) * _this2.options.pageSize : pageNum * _this2.options.pageSize; //获取当前总页数

                    if (_this2.app[i]) {
                        if (_this2.type === "more") {
                            if (startPage < _this2.app[i].json.length) {
                                _this.options.beforeMount();

                                _this2.app[i].datasource.datasource = _this2.app[i].json.slice(startPage, endPage); // dom.attr('data-page-num',pageNum).attr('disabled',false).text(this.options.isHasMore)
                            } else {
                                dom.text(_this2.options.isNoMore);
                            }
                        } else {
                            _this2.app[i].datasource.datasource = _this2.app[i].json.slice(startPage, endPage);
                        }
                    } else {
                        var _this3 = _this2;
                        var label = _this2.options.template.replace(/^\s+|\s+$/g, "")[1] === "l" ? "ul" : "div";
                        var fn = new Vue({
                            el: "#".concat(id),
                            data: function data() {
                                return {
                                    datasource: {
                                        datasource: [{
                                            titleImages: [{
                                                imageUrl: ""
                                            }]
                                        }]
                                    },
                                    json: []
                                };
                            },
                            mounted: function mounted() {
                                var _this4 = this;

                                $.ajax({
                                    url: url,
                                    type: "GET",
                                    dataType: "json"
                                }).then(function (res) {
                                    // console.log(res);
                                    _this4.json = res.datasource;
                                    if (startPage <= _this4.json.length) {
                                        _this3.options.beforeMount();
                                        _this4.datasource = res;
                                        _this4.datasource.datasource = _this4.json.slice(startPage, endPage);
                                    } else {
                                        dom.html(_this3.options.isNoMore);
                                    }
                                });
                            },
                            updated: function updated() {
                                var html = $("#" + vueId).html();

                                if (_this3.type === "more") {
                                    // console.log(component.find(_this.itemNode).children().last());
                                    // $(html).insertAfter(component.find(_this.itemNode).children().last())
                                    component.append(html);

                                    _this3.options.updated(startPage, endPage);

                                    dom.attr("disabled", false).html(_this3.options.isHasMore);
                                } else {
                                    component.find(_this3.itemNode).parent().html(html);
                                }

                                _this3.options.updated();
                            },
                            filters: _objectSpread({}, _this3.filters),
                            template: "<".concat(label, ' id="').concat(vueId, '" style="display: none;">\n                ').concat(_this3.options.template, "\n              </").concat(label, ">\n              ")
                        });
                        _this2.app[i] = fn;
                    }
                });
            });
        }
    }, {
        key: "findLableName",
        value: function findLableName(data) {
            var dom = document.createElement("div");
            dom.innerHTML = data;
            var name = dom.firstChild.id ? "#" + dom.firstChild.id : dom.firstChild.classList.length ? "." + dom.firstChild.classList[0] : "";
            return name;
        }
        /**
         * 随机生成由字母+数字的字符串
         */
    }, {
        key: "randomWord",
        value: function randomWord(randomFlag, min, max, isFirst) {
            if (typeof max === "string" && !randomFlag) {
                isFirst = max;
                max = null;
            } // randomFlag: Boolean 是否随机个数
            // min 最少个数
            // max 最大个数

            var str = "";
            var range = min;
            var arr = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]; // 随机产生

            if (randomFlag) {
                range = Math.round(Math.random() * (max - min)) + min;
            }

            var pos = "";

            if (isFirst) {
                str = isFirst;
            }

            for (var i = 0; i < range; i++) {
                pos = Math.round(Math.random() * (arr.length - 1));
                str += arr[pos];
            }

            return str;
        }
    }, {
        // 提取json地址
        key: 'extractUrl',
        value: function extractUrl() {
            var _this2 = this;

            var component = $(_this2.options.parentNode);

            if (component.length > 1) {
                component = dom.parent().find(_this2.options.parentNode) || dom.parent().parent().find(_this2.options.parentNode) || dom.parent().parent().parent().find(_this2.options.parentNode);
            } // 获取数据请求地址

            var url = _this2.options.url;

            if (!url) {
                // 获取组件datasource
                var dataAttr = component.attr("data");
                var datatype = component.attr("datatype");
                var datasource = _this2.options.datasource || dataAttr ? dataAttr.split(":")[1] : "";
                var preview = datatype == "category" ? "category_" : component.attr("preview"); // let sourceUrl = '.' + (datasource ? `${this.pathname.indexOf('/index.html') > 0 ? this.pathname.slice(0,-11) :
                //  this.pathname}/${preview}${datasource}.json` : '');

                var sourceUrl = datasource ? "./".concat(preview).concat(datasource, ".json") : "";
                url = sourceUrl || _this2.vUrl;
            }
            return url;
        }
    }]);

    return Xhwpage;
}();
// }
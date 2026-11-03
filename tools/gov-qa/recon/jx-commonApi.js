var commonApi = {
    /**
     * @param {object} data 数融标签获取栏目下稿件
     * <ucap:articleListIncludeTag></ucap:articleListIncludeTag>
     * @param {object} config 数据重组条件配置
     * config: {
        pageSize: number, //取几条数据 （注意pageSize参数！！！getQueryList方法写在parmas中；addArticleList写在config中）
        分页条数取值优先级：调用方法传参 -> 页面pageSize元素 -> config.js中默认配置
        startIndex: 0, //从第几条开始取
        isSummary: false, //是否显示摘要。默认不传,false
        isRelation: false, //是否显示关联稿件
        isContent: false //是否取正文
        isWebSearch: false, // 是否接口数据,无需手动传，当调用getQueryList方法时，自动传过来
     * }
     * @param {object} fn 回调函数 
     * fn:{
        listDom: '',//显示数据容器
        createHtml: fn, //单条数据创建html标签
        callback: fn,//有数据回调函数
        noDataCbk: fn,//无数据回调
    * }
     * 
     */
    addArticleList: function (data, config, fn) {
        if (data && data.length) {
            var pageSize = config.pageSize || $("#pageSize").val() || defaultConfig.pageSize;
            var _lihtm = "";
            var startIndex = config.startIndex || 0;
            $(fn.listDom).html('')
            data = data.slice(startIndex, config.pageSize && (startIndex + config.pageSize));
            data.forEach(function (item, index) {
                if (index < pageSize) {
                    var itemObj = '';
                    if (config.isWebSearch) {
                        itemObj = item.source;
                        itemObj._manuscriptId = item.id;
                    } else {
                        itemObj = item;
                    }
                    commonApi.addDataAttr(itemObj, config);
                    if (fn.createHtml) {
                        _lihtm += fn.createHtml(itemObj, index);
                    }

                    if (fn.listDom && fn.createHtml) {
                        $(fn.listDom).html(_lihtm);
                    };

                }
            })
            fn.callback && fn.callback(data);
        } else {
            fn.noDataCbk && fn.noDataCbk(data);
        }
    },

    // 概览页点击分页调取数据
    /**
     * @param {object} parmas - getQueryList分页接口参数
     * params: {
         current: 1, //当前第几页
         pageSize: number,//一页返回几条数据。分页条数取值优先级：调用方法传参 -> 页面pageSize元素 -> config.js中默认配置
         channelCode: [], //栏目代号
         webSiteCode: [], //站点代号
         filterTopData: [], //稿件ID，过滤数据
         havePictures: false, // boolean 是否查询带有图片的稿件，默认false, 查询传true
    * }
     * @param {object} config 数据重组条件配置
     * config: {
        pageSize: number, //取几条数据 （注意pageSize参数！！！getQueryList方法写在parmas中；addArticleList写在config中）
        startIndex: 0, //从第几条开始取
        isSummary: false, //是否显示摘要
        isRelation: false, //是否显示关联稿件
        isContent: false //是否取正文
        isWebSearch: false, // 是否接口数据,无需手动传，当调用getQueryList方法时，自动传过来
     * }
     * @param {object} fn 回调函数 
     * fn:{
        listDom: '',//显示数据容器
        pageDom:'', //分页容器
        createHtml: fn, //单条数据创建html标签
        callback: fn,//有数据回调函数
        noDataCbk: fn,//无数据回调
    * }
    */
    getQueryList: function (parmas, config, fn) {
        var pageSize = parmas.pageSize || $("#pageSize").val() || defaultConfig.pageSize;
        var _parmas = ''
        if(fn.isContent == false){
             _parmas = $.extend({ 
            current: 1,
            pageSize: pageSize,
            webSiteCode: [window.websiteCode || ''],
            notReturnContent:true
        }, parmas);
        }else{
             _parmas = $.extend({ 
                current: 1,
                pageSize: pageSize,
                webSiteCode: [window.websiteCode || '']
            }, parmas);
        }
        // var _thisFn = arguments.callee;
        var url = ajaxUrl.sr.webSearch.queryList,
            isQueryList = true; //getQueryList和searchManuscript接口返回的数据结构不同，getQueryList主要内容在source字段下
        if (parmas.channelTreeIds || parmas.title || parmas.Contenthtml || parmas.isSearchHighlight) {
            //传了以上参数，则使用searchManuscript接口
            url = ajaxUrl.sr.webSearch.searchManuscript
            isQueryList = false
        }
        $.ajax({
            url: url,
            type: 'POST',
            data: _parmas,
            success: function (res) {
                if (res.data.results && res.data.results.length > 0) {
                    commonApi.addArticleList(res.data.results, $.extend(config, {
                        isWebSearch: isQueryList,
                        pageSize: pageSize
                    }), fn);

                    //概览页分页
                    if (fn.pageDom) {
                        commonApi.getArticlePage(res.data, _parmas, config, fn)
                    }

                } else {
                    fn.noDataCbk && fn.noDataCbk(data);
                }
            },
            error: function (err) {
                console.log(err)
            }
        })
    },

    //概览页分页
    getArticlePage: function (data, parmas, config, fn) {
        var pageCount = data.total % parmas.pageSize > 0 ? 1 + parseInt(data.total / parmas.pageSize) : parseInt(data.total / parmas.pageSize)
        if (pageCount > 1) {
            if (fn.pageDom == '.page-circle') { //另一种分页样式
                $(fn.pageDom).pagination({
                    pageCount: pageCount,
                    count: 2,
                    prevContent: '<font class="none">上一页</font><i class="arrow arrow-left"></i>',
                    nextContent: '<font class="none">下一页</font><i class="arrow arrow-right"></i>',
                    callback: function (api) {
                        commonApi.getQueryList($.extend(parmas, {
                            current: api.getCurrent()
                        }), $.extend(config, {
                            isWebSearch: true
                        }), fn)
                    }
                });
            } else {
                $(fn.pageDom).pagination({
                    pageCount: pageCount,
                    current: parmas.current,
                    jump: true,
                    coping: true,
                    homePage: '首页',
                    endPage: '末页',
                    count: 2,
                    prevContent: '<font class="none">上一页</font><i class="arrow arrow-left"></i>',
                    nextContent: '<font class="none">下一页</font><i class="arrow arrow-right"></i>',
                    total: true,
                    totalData: data.total,
                    callback: function (api) {
                        var apiCurrent = api.getCurrent();
                        var _parmas = {
                            current: api.getCurrent()
                        }
                        if (data.total == 10000) {
                            var lastPageSize = 10000 % parmas.pageSize;
                            if (apiCurrent == pageCount) {
                                _parmas.pageSize = lastPageSize
                            }
                        }
                        console.log(_parmas)
                        commonApi.getQueryList($.extend(parmas, _parmas), $.extend(config, {
                            isWebSearch: true
                        }), fn)
                    }
                });
            }
        } else if (pageCount == 1) {
            $(fn.pageDom).hide();
        }
    },

    //重组返回的数据
    addDataAttr: function (itemObj, config) {
        itemObj._time = commonApi.editData.getDate(itemObj);
        itemObj._url = commonApi.editData.getUrl(itemObj);
        itemObj._images = commonApi.editData.getImages(itemObj);
        itemObj._summary = itemObj.summary || '';
        itemObj._articleFiles = commonApi.editData.getArticleFiles(itemObj);
        if (config.isContent) { //是否正文
            itemObj._content = (itemObj.content && itemObj.content.content) || '';
        }
        if (config.isSummary && !itemObj._summary) { //是否用正文填充摘要
            itemObj._summary = itemObj.content && itemObj.content.content.replace(/<.*?>/g, "").trim();
        }
        if (config.isRelation && itemObj.relationUrl) {
            itemObj._relation = commonApi.editData.handerRelation(itemObj.relationUrl);
        }
        //元数据
        if (itemObj.metadata && (typeof itemObj.metadata == 'string')) {
            itemObj._metadata = JSON.parse(itemObj.metadata);
        }

    },

    //概览页关联稿件
    addRelationArticle: function (data, dom, pageSize, createHtml, callback) {
        var pageSize = pageSize || 10;
        if (data && data.length) {
            var relationStr = '';
            data.forEach(function (item, index) {
                if (index < pageSize) {
                    item._urls = commonApi.editData.getUrl(item);
                    if (createHtml) {
                        relationStr += createHtml(item)
                    } else {
                        relationStr += '<li><a target="_blank" title="' + item.title + '" href="' + item._urls + '">' + item.title + '</a><span class="time">' + item.pubDate.substring(0, 10) + '</span></li>';
                    }
                }
            })
            $(dom).html(relationStr);
            callback && callback();
        }
    },

    //添加网站归档信息
    addChannelTag: function (data, websiteData, dom) {
        //data当前栏目数据 websiteData网站基本信息 dom添加归档信息的dom元素
        //示例：
        //var channelsTag = <ucap:channelsTag></ucap:channelsTag>;
        //addChannelTag(channelsTag,'.right-content');
        var fileFlag = ((data && data.fileFlag) || (data && data.archiveStatus) || '') + ''
        if (fileFlag === '1') {
            $(dom).append('<div class="water-mark"><img src="' + websiteData.watermarkUrl + '"/></div>')
        }
    },

    // 文章页相关附件
    addAppendixArticle: function (data, dom, callback) {
        //data关联稿件数据 listDom添加关联稿件的dom元素
        //示例：
        // var articleAppendix = ${articleFiles};
        // commonApi.addAppendixArticle(articleAppendix, '.article-appendix .infolist');
        // console.log('appendixData',data);
        if (!data) return;
        if (typeof data === 'string') {
            data = JSON.parse(data);
        }
        // data = data && data.length ? data[0] : [];
        if (data && data.length && JSON.stringify(data[0]) !== "{}") {
            var appendixStr = "";
            data.forEach(function (item) {
                appendixStr += '<li><a target="_blank" href="' + item.filePath + '">' + item.fileName + '</a></li>';
            })
            $(dom).html(appendixStr);
            callback && callback();
        }
    },

    //添加面包屑导航
    addCrumbs: function (data, breadDom) {
        //data当前栏目数据 breadDom添加面包屑的dom元素
        if (!data || $(breadDom).length == 0) return;
        if (data.crumbs && data.crumbs.length) {
            if (data.crumbs && data.crumbs.length) {
                var breadHtm = "<a href='/" + websiteCode + "/'>首页</a>";
                var len = data.crumbs.length;
                for (var i = 0; i < len; i++) {
                    var crumbItem = data.crumbs[i];
                    var cls = i == len - 1 ? 'class="on"' : '';
                    var _url = crumbItem.redirectUrl || crumbItem.redirectLink || (crumbItem.urls && crumbItem.urls.pc) || 'javascript:void(0);';
                    breadHtm += ' > <a ' + cls + ' href="' + _url + '" >' + crumbItem.name + '</a>'
                }
            }
            $(breadDom).html(breadHtm);
        }
    },


    //添加上下篇
    addSxp: function (data, manuscriptId, dom) {
        if (!(data && data.length)) return;
        var len = data.length;
        $(data).each(function (index, item) {
            if (item.id == manuscriptId) {
                if (index - 1 >= 0) {
                    var prev = data[index - 1];
                    $(dom).append('<li><span>上一篇：</span><a href="' + commonApi.editData.getUrl(prev) + '">' + prev.title + '</a></li>');
                }
                if (index + 1 <= len - 1) {
                    var next = data[index + 1];
                    $(dom).append('<li><span>下一篇：</span><a href="' + commonApi.editData.getUrl(next) + '">' + next.title + '</a></li>');
                }
            }
        })
    },

    //添加标签
    /**
     * @param {string} data - 数据源（标签多个以,号分割）
     * @param {*} dom - 容器
     * @param {*} callback - 回调函数
     * @returns 
     */
    addTags: function (data, dom, callback) {
        if (!data) return;
        if (typeof data === 'string') {
            data = data.split(',');
        }
        if (!(data && data.length)) return;
        if (dom) {
            var tagHtm = '<b>标签</b>';
            $(data).each(function (index, item) {
                if (item) tagHtm += '<a>' + item + '</a>';
            })
            $(dom).html(tagHtm);
        } else {
            callback && callback(data)
        }
    },

    //处理数据
    editData: {
        //url处理
        getUrl: function (itemObj, mode) { //mode：模板组代号
            if (!itemObj) return;
            var _urlsObj = itemObj.urls && JSON.parse(itemObj.urls),
                _urls = _urlsObj && (_urlsObj[mode] || _urlsObj.pc),
                _url = itemObj.redirectUrl || itemObj.redirectLink || _urls;
            if (itemObj.attDownloadType == 1) {
                var articleFiles = itemObj.articleFiles[0]
                // console.log(itemObj.articleFiles[0])
                if (articleFiles.filePath != null) {
                    _url = articleFiles.filePath;
                } else if (articleFiles.notype.length > 0) {
                    _url = articleFiles.notype[0].filePath;
                }

                // var articleFiles = commonApi.editData.getArticleFiles(itemObj);
                // if (articleFiles.files.length > 0) {
                //     _url = articleFiles.files[0].filePath;
                // } else if (articleFiles.notype.length > 0) {
                //     _url = articleFiles.notype[0].filePath;
                // }
            }
            return _url;
        },
        //处理图片
        getImages: function (itemObj) {
            if (!itemObj) return;
            var _images = {};
            if (itemObj.images && typeof itemObj.images == 'string' && JSON.parse(itemObj.images).length) {
                _images = JSON.parse(itemObj.images)[0];
            } else if (typeof itemObj.images == 'object' && itemObj.images.length) {
                _images = itemObj.images[0];
            }
            // _images.cover = _images.cover || commonApi.noPic;
            //优先级：封面图 - 附件第一张图 - 无图
            var _articleFiles = commonApi.editData.getArticleFiles(itemObj);
            _images.cover = _images.cover || (_articleFiles.images && _articleFiles.images.length && _articleFiles.images[0].filePath) || commonApi.noPic;
            return _images;
        },
        // 发布日期格式调整
        getDate: function (itemObj) {
            if (!itemObj) return;
            var _time = {},
                time = itemObj.pubDate;
            _time.yyyyMMdd = time.substring(0, 10);
            _time.MMdd = time.substring(5, 10);
            _time.yyyy = time.substring(0, 4);
            _time.dd = time.substring(8, 10);
            _time.yyyyMM = time.substring(0, 7);
            _time.yyyyMMddDot = _time.yyyyMMdd.split('-').join('.');
            return _time;
        },
        //处理附件列表，封面图有可能放在附件列表, type 默认0，0：附件，1:图片，2：音频，3：视频
        getArticleFiles: function (itemObj) {

            if (!itemObj) return;
            var articleFiles = [];
            var _articleFiles = {
                files: [],
                images: [],
                audios: [],
                videos: []
            };

            if (itemObj.articleFiles && typeof itemObj.articleFiles == 'string' && JSON.parse(itemObj.articleFiles).length) {
                articleFiles = JSON.parse(itemObj.articleFiles);
            } else if (typeof itemObj.articleFiles == 'object' && itemObj.articleFiles.length) {
                articleFiles = itemObj.articleFiles;
            }
            if (articleFiles.length > 0) {
                $.each(articleFiles, function (i, elem) {
                    if (elem.type == 0) {
                        _articleFiles.files.push(elem)
                    }
                    if (elem.type == 1) {
                        _articleFiles.images.push(elem)
                    }
                    if (elem.type == 2) {
                        _articleFiles.audios.push(elem)
                    }
                    if (elem.type == 3) {
                        _articleFiles.videos.push(elem)
                    }

                    if (!elem.type && elem.cover) {
                        _articleFiles.images.push(elem)
                    }
                })
            }
            return _articleFiles;
        },
        addTags: function (data) {
            if (!data) return '';
            if (typeof data === 'string') {
                data = data.split(',');
            }
            if (!(data && data.length)) return '';
            var _lihtm = "";
            $(data).each(function (index, item) {
                if (item.classify) {
                    var url = commonApi.editData.getUrl(item);
                    _lihtm += '<a target="_blank" href=' + url + ' class="tag">' + item.classify + '</a>';
                } else {
                    _lihtm += '<a class="tag">' + item + '</a>';
                }

            })
            return _lihtm
        },
        cutString: function (str, num) {
            return str.length > num ? str.substr(0, num) + '...' : str;
        },
        handerRelation: function (relationUrl) {
            var relation;
            $.ajax({
                url: relationUrl,
                type: "GET",
                dataType: "json",
                async: false,
                success: function (e) {
                    e.forEach(function (item) {
                        var classifyName = item.classify;
                        if (classifyName == '文字解读') {
                            item.classify = '解读';
                        } else if (classifyName == '音视频（动漫）解读') {
                            item.classify = '动漫解读';
                        } else if (classifyName == '图文解读') {
                            item.classify = '图解';
                        }
                    })
                    relation = e;
                }
            })
            return relation;
        },
    },

    //聚合栏目
    getArticleLists: function (cTag, dom, pageSize, createItemHtmlFn, createListHtmlFn, callbackFn) {
        if (cTag && cTag.children.length > 0) {
            var _itemHtml = '';
            cTag.children.forEach(function (item, index) {
                if (item.showOrNot == 1) {
                    item._url = commonApi.editData.getUrl(item);
                    _itemHtml += createItemHtmlFn && createItemHtmlFn(item);
                }
            })
            $(dom).html(_itemHtml);

            cTag.children.forEach(function (item, index) {
                //聚合栏目
                let ppp={
                    current: 1,
                    pageSize: pageSize,
                    channelCode: [item.code],
                    webSiteCode: [websiteCode],
                    channelTreeIds: [item.id]
                }
                //聚合兼容260331
                if(item.aggregationChannel=='1'&&item.aggChannelIds){
                    ppp={
                        current: 1,
                        pageSize: pageSize,
                        webSiteCode: [],
                        channelId:item.aggChannelIds.split(',')
                    }
                }
                commonApi.getQueryList(ppp, null, {
                    listDom: '#data-channel-' + item.code,
                    createHtml: createListHtmlFn,
                    callback: callbackFn
                });
            })
        }
    },

    //获取子栏目导航
    getChannelsNav: function (channelsTag, dom, pageSize, createHtml) {
        if (!channelsTag || channelsTag.children.length == 0) return;
        var navHtm = '';
        var pageSize = pageSize || channelsTag.children.length;
        channelsTag.children.sort(function (a, b) {
            return a.sort - b.sort;
        });
        channelsTag.children.forEach(function (elem, index, array) {
            if (elem.showOrNot && index < pageSize) {
                if (createHtml) {
                    navHtm += createHtml(elem);
                } else {
                    navHtm += '<li><a title="' + elem.name + '" href="' + commonApi.editData.getUrl(elem) + '">' + elem.name + '</a><font>|</font></li>';
                }
            }
        })
        $(dom).html(navHtm);
    },

    //获取子栏目-栏目代号数组集合
    getChildCodes: function (cTag) {
        if (!cTag.children || cTag.children.length == 0) return;
        var codeArr = [];
        cTag.children.forEach(function (elem) {
            codeArr.push(elem.code);
        })
        return codeArr;
    },

    //获取地址参数
    getParams: function (name) {
        var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)')
        var r = window.location.search.substr(1).match(reg)
        if (r != null) return decodeURI(r[2])
        return null
    },

    //通过id查询稿件
    getContentById: function (id, callback) {
        $.ajax({
            url: ajaxUrl.sr.webSearch.getManuscriptById,
            type: 'get',
            data: {
                id: id
            },
            success: function (res) {
                if (res.data.results && res.data.results.length > 0) {
                    var content = res.data.results[0].content.content || '';
                    callback(content)
                } else {
                    callback('')
                }
            },
            error: function (err) {
                console.log(err)
            }
        })
    },

    //设置归档水印
    setGdWatermark: function (channelsTagSelf, channelsTagParent, callback) {
        if (!channelsTagSelf) return;
        var fileTime = channelsTagSelf.fileTime;
        // 父栏目
        if (window.channelsTagParent && channelsTagParent.length > 0 && channelsTagParent[0].fileTime) {
            fileTime = channelsTagParent[0].fileTime;
        }
        if (fileTime) {
            var gdDate = new Date(Number(fileTime)),
                year = gdDate.getFullYear(),
                month = gdDate.getMonth() + 1,
                day = gdDate.getDate();
            gdDate = year + '-' + (month > 9 ? month : '0' + month) + '-' + (day > 9 ? day : '0' + day);
            callback && callback(gdDate);
        }
    },
    /**
     * 消息弹窗
     * @param {object} opts 选项
     * messag: string 消息内容
     * delay: number 显示时长
     */
    message: function (opts) {
        // 移除之前
        var modals = document.querySelectorAll('.message-tip-modal');
        modals.forEach(function (modal) {
            modal.parentNode.removeChild(modal);
        })
        // 追加新的
        var el = document.createElement('div');
        el.classList.add('message-tip-modal');
        var html = '<div class="message-tip">\
                <div class="message-tip-content">' + opts.message + '</div>\
            </div>';
        el.innerHTML = html;
        document.body.appendChild(el);
        // 显示时长控制
        //      setTimeout(() => {
        //          el.parentNode.removeChild(el);
        //          if (opts.cb) {
        //              opts.cb();
        //          }
        //      }, opts.delay || 1500);
        setTimeout(function () {
            el.parentNode.removeChild(el);
            if (opts.cb) {
                opts.cb();
            }
        }, opts.delay || 1500)
    },
    filtersName: function (str) {
        if (null != str && str != undefined) {
            if (str.length == 2) {
                return str.substring(0, 1) + '*'; //截取name 字符串截取第一个字符，
            } else if (str.length == 3) {
                return str.substring(0, 1) + "*" + str.substring(2, 3); //截取第一个和第三个字符
            } else if (str.length > 3) {
                return str.substring(0, 1) + "*" + '*' + str.substring(3, str.length); //截取第一个和大于第4个字符
            }
        } else {
            return "";
        }
    },
    // 手机号隐藏过滤
    filtersPhone: function (str) {
        if (null != str && str != undefined) {
            return str.replace(/^(.{3})(?:\d+)(.{4})$/, "$1****$2");
        } else {
            return "";
        }
    },
    /**
     * AES解密
     * @param {*} data 需要解密的密文
     * @returns 
     * 例子 aesDecrypt(data)
     */
    aesDecrypt: function (data) {
        var secretKey = '12345678abcdefgh';
        var key = CryptoJS.enc.Utf8.parse(secretKey);
        var iv = CryptoJS.enc.Utf8.parse(secretKey);
        var decrypted = CryptoJS.AES.decrypt(data, key, {
            iv: iv,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        });
        return decodeURI(decrypted.toString(CryptoJS.enc.Utf8));
    },
    // 去除HTML标签方法
    removeHtmlTags: function (str) {
        return str.replace(/<[^>]*>/g, '');
    },
    extractContentFromPTag: function(htmlString) {
    // 创建一个临时的 DOM 元素
    var $temp = $('<div>').html(htmlString);
    // 提取 p 标签的内容
    var content = $temp.text();
    return content;
    }
};

var createHtmlFn = {
    //通用列表
    infolist: function (item) {
        return '<li><a target="_blank" title="' + item.title + '" href="' + item._url + '">' + item.title + '</a></li>';
    },
    //通用列表 MMdd
    infolistMd: function (item) {
        return '<li><a target="_blank" title="' + item.title + '" href="' + item._url + '">' + item.title + '</a><span class="time">' + item._time.MMdd + '</span></li>';
    },
    //通用列表yyyyMMdd
    infolistYmd: function (item) {
        return '<li><a target="_blank" title="' + item.title + '" href="' + item._url + '">' + item.title + '</a><span class="time">' + item._time.yyyyMMdd + '</span></li>';
    }
};
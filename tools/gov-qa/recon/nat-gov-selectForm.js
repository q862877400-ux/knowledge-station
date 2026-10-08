let formIndex = 0
let selectedValues = []
let notSelect = null
$(function () {
    $(document).ready(function () {
        // 点击自定义单选框时
        // $(".option_item").click(function () {
        //     // 移除同组中其他所有选项的选中样式和状态
        //     $(".option_item").not(this).children(".radio").text("")

        //     // 给当前点击的选项添加选中样式
        //     $(this).children(".radio").text("✓‌")

        //     // 可选：获取当前选中的值
        //     selectValue = $(this).data("value")
        // })
        let selectedCount = 0

        $(".option_item").click(function () {
            const $radio = $(this).children(".radio")
            const isSelected = $radio.text() === "✓‌"

            // 如果已经选中，点击则取消选择
            if (isSelected) {
                $radio.text("")
                selectedCount--
            }
            // 如果未选中且未达到最大选择数量，点击则选中
            else if (selectedCount < 3) {
                $radio.text("✓‌")
                selectedCount++
            }
            $('.claNum').text(selectedCount)
            // 控制其他选项的禁用状态
            if (selectedCount === 3) {
                // 给所有未选中的选项添加disabled类
                $(".option_item").each(function () {
                    if ($(this).children(".radio").text() !== "✓‌") {
                        $(this).addClass("disabled_option")
                    }
                })
            } else {
                // 当选中数量小于4时，移除所有选项的disabled类
                $(".option_item").removeClass("disabled_option")
            }
            const ary = []
            // 可选：获取所有选中的值
            $(".option_item").each(function () {
                if ($(this).children(".radio").text() === "✓‌") {
                    ary.push($(this).data("value"))
                }
            })
            selectedValues = ary
            // 现在selectedValues数组中包含了所有选中项的值
        })
        function objToQueryString(obj) {
            return Object.keys(obj)
                .map(
                    (key) =>
                        encodeURIComponent(key) +
                        "=" +
                        encodeURIComponent(obj[key])
                )
                .join("&")
        }

        // 生成带参数的URL
        $("#select_sub").click(function () {
            if (!selectedValues.length) {
                prompt2("请选择关键词后再点击开始留言！", "确定")
            } else {
                const params = {
                    params: selectedValues.join(",") + "&" + formIndex
                }
                var queryString = objToQueryString(params)
                location.href = "./index_form.htm?" + queryString
            }
        })
        $("#select_skip").click(function () {
            const params = {
                params: notSelect + "&" + formIndex
            }
            var queryString = objToQueryString(params)
            location.href = "./index_form.htm?" + queryString
        })
        $(".nmgqx-enter-btn1").on("click", function (e) {
            window.open(
               // "https://www.mohrss.gov.cn/SYrlzyhshbzb/rdzt/gznmgqxwt/tqnmggzxsfy/",
               "https://www.mohrss.gov.cn/SYrlzyhshbzb/zxhd/",
                "_blank"
            )
            e.stopPropagation()
        })
        $(".nmgqx-enter-btn2").on("click", function (e) {
            window.open(
                "https://sme-dj.miit.gov.cn/index.html#/page/portal",
                "_blank"
            )
            e.stopPropagation()
        })
    })
})

function prompt2(html, btnTxt, cb, h3Txt) {
    var prompt = $(".prompt2")
    var nr = $(".nr", prompt)
    var h3 = $("h3", prompt)
    var img = $("img", prompt)
    var btn = $("button", prompt)
    var black = $(".bg-black")
    black.show()
    prompt.show()
    nr.html(html)
    if (typeof btnTxt != "undefined" && btnTxt != "") {
        btn.text(btnTxt)
    } else {
        btn.text("确定")
    }
    if (typeof h3Txt != "undefined" && h3Txt != "") {
        h3.text(h3Txt)
        if (h3Txt.indexOf("成功") != -1) {
            img.attr("src", "images/h123.png")
        }
    } else {
        h3.text("")
        img.attr("src", "images/h125.png")
    }
    btn.unbind("click").on("click", function () {
        $(".bg-black").hide()
        $(this).parents(".prompt2").hide()
        if (typeof cb != "undefined") {
            cb()
        }
    })
}
const classifyUrl = comUrl + "/commons/dictionary?code=netizen_category"
// 获取问题
function getClassify() {
    $.ajax({
        cache: true,
        type: "GET",
        url: classifyUrl,
        async: false,
        error: function (error) {},
        success: function (res) {
            notSelect = res.data.find((it) => {
                return it.name === "用户未选择"
            })
            notSelect = notSelect.code + "-" + notSelect.children[0].code
            $(document).ready(function () {
                const domStr = res.data
                    .map((it) => {
                        if (it.name === "用户未选择") {
                            return ""
                        }
                        return `
				<div class="select_content">
					<div class="select_item">
						<div class="item_title">${it.name}</div>
						<div class="item_options">
                            ${it.children
                                .map((item) => {
                                    if (item.name === "用户未选择") {
                                        return ""
                                    }
                                    return `
                                    <div class="option_item" data-value="${
                                        it.code + "-" + item.code
                                    }">
                                        <div class="radio"></div>
                                        <div class="text">${item.name}</div>
                                    </div>`
                                })
                                .join("")}
						</div>
					</div>
				</div>`
                    })
                    .join("")
                var newElement = $(domStr)
                // 使用 before() 方法在 id 为 targetDiv 的元素之前插入新元素
                $(".select_btn").before(newElement)
            })
        }
    })
}
getClassify()

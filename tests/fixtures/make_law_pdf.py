"""生成合成法条 PDF（测试 fixture）：编-章-节-条 结构 + 编号条款。

覆盖 legal 分型关键要素：义务主体（经营者/个人信息处理者）、
模态（应当/不得/可以）、但书例外、内部引用（依照本法第X条）。
运行: python tests/fixtures/make_law_pdf.py [输出路径]
"""
from pathlib import Path
import sys

import fitz

ARTICLES = [
    # (条号, 正文)
    ("第一条", "为了保护个人信息权益，规范个人信息处理活动，制定本法。"),
    ("第二条", "处理个人信息应当遵循合法、正当、必要和诚信原则。"),
    ("第三条", "个人信息处理者处理个人信息应当取得个人同意，但法律、行政法规另有规定的除外。"),
    ("第四条", "个人信息处理者不得过度收集个人信息，不得因个人拒绝提供信息而拒绝提供基本服务。"),
    ("第五条", "处理敏感个人信息应当取得个人的单独同意。"),
    ("第六条", "个人信息处理者不得泄露、篡改、丢失个人信息；发生泄露的，应当立即采取补救措施。"),
    ("第七条", "经营者不得利用格式条款和技术手段，排除或者限制消费者权利。"),
    ("第八条", "经营者应当保证消费者享有知悉其购买商品真实情况的权利。"),
    ("第九条", "消费者享有对商品和服务进行监督的权利，可以提出批评和建议。"),
    ("第十条", "依照本法第五条的规定处理敏感个人信息的，应当进行个人信息保护影响评估。"),
    ("第十一条", "违反本法规定处理个人信息的，由履行个人信息保护职责的部门责令改正，没收违法所得。"),
    ("第十二条", "个人信息处理者可以委托他人处理个人信息，但应当与受托人约定处理目的和期限。"),
]


def make_law_pdf(out_path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 80
    page.insert_text((72, 60), "中华人民共和国个人信息保护法（测试节选）",
                     fontsize=16, fontname="china-s")
    for no, text in ARTICLES:
        page.insert_text((72, y), no, fontsize=12, fontname="china-s")
        page.insert_text((110, y), text, fontsize=12, fontname="china-s")
        y += 28
        if y > 780:
            page = doc.new_page(width=595, height=842)
            y = 80
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    doc.close()
    return out_path


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("var/fixtures/测试法.pdf")
    print(make_law_pdf(target))

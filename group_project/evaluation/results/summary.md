| Metric | Config A | Config B | Delta B−A |
|---|---:|---:|---:|
| faithfulness | 0.877 | 0.925 | 0.048 |
| answer_relevancy | 0.964 | 0.973 | 0.009 |
| context_recall | 1.000 | 1.000 | 0.000 |
| context_precision | 0.852 | 0.753 | -0.099 |
| average | 0.923 | 0.913 | -0.011 |
| hit_at_k | 1.000 | 1.000 | 0.000 |
| mrr | 0.944 | 0.944 | 0.000 |
| latency_s | 7.472 | 3.572 | -3.899 |
| refusals | 0 | 0 | |

Worst performers (average of 4 metrics):

| Config | ID | Question | Faith | Relev | Recall | Prec | hit | sources |
|---|---|---|---:|---:|---:|---:|---|---|
| A_dense | q08 | Phở có nguồn gốc từ đâu? | 0.875 | 0.933 | 1.000 | 0.000 | True | wiki-pho, wiki-pho, wiki-pho |
| B_hybrid | q12 | Mức ký quỹ kinh doanh dịch vụ lữ hành nội địa hiện nay là bao nhiêu? | 0.333 | 0.991 | 1.000 | 0.500 | True | nghi-dinh-168-2017-huong-dan-luat-du-lich, nghi-dinh-94-2021-ky-quy-lu-hanh, luat-du-lich-2017 |
| B_hybrid | q08 | Phở có nguồn gốc từ đâu? | 0.875 | 0.958 | 1.000 | 0.000 | True | wiki-pho, wiki-pho, wiki-pho |
| A_dense | q12 | Mức ký quỹ kinh doanh dịch vụ lữ hành nội địa hiện nay là bao nhiêu? | 0.333 | 1.000 | 1.000 | 0.500 | True | nghi-dinh-168-2017-huong-dan-luat-du-lich, nghi-dinh-94-2021-ky-quy-lu-hanh, luat-du-lich-2017 |
| B_hybrid | q15 | Khách du lịch có những quyền gì theo Luật Du lịch? | 1.000 | 0.991 | 1.000 | 0.250 | True | luat-du-lich-2017, luat-du-lich-2017, luat-du-lich-2017 |
| B_hybrid | q14 | Theo Luật Du lịch 2017, du lịch được định nghĩa như thế nào? | 1.000 | 1.000 | 1.000 | 0.250 | True | luat-du-lich-2017, nghi-dinh-168-2017-huong-dan-luat-du-lich, luat-du-lich-2017 |
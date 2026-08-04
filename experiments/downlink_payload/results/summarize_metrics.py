import csv, statistics, pathlib

def summarize(path, tag):
    rows=list(csv.DictReader(pathlib.Path(path).open(encoding='utf-8')))
    raw=[float(r['raw_image_bytes']) for r in rows]
    full=[float(r['full_yolo_json_bytes']) for r in rows]
    structured=[float(r['structured_json_bytes']) for r in rows]
    summary=[float(r['summary_bytes']) for r in rows]
    r1=[float(r.get('raw_to_structured_ratio') or 0) for r in rows]
    r2=[float(r.get('raw_to_summary_ratio') or 0) for r in rows]
    print(f'[{tag}] n={len(rows)}')
    print(f'raw_mean={statistics.mean(raw):.2f} raw_min={min(raw):.0f} raw_max={max(raw):.0f}')
    print(f'full_json_mean={statistics.mean(full):.2f} structured_mean={statistics.mean(structured):.2f} summary_mean={statistics.mean(summary):.2f}')
    print(f'raw_to_structured mean={statistics.mean(r1):.3f} min={min(r1):.3f} max={max(r1):.3f}')
    print(f'raw_to_summary mean={statistics.mean(r2):.3f} min={min(r2):.3f} max={max(r2):.3f}')
    for rate in ('9.6','100','1000'):
        k_raw=f'raw_image_bytes_tx_s_at_{rate}_kbps'
        k_struct=f'structured_json_bytes_tx_s_at_{rate}_kbps'
        k_sum=f'summary_bytes_tx_s_at_{rate}_kbps'
        med_raw=statistics.median(float(r[k_raw]) for r in rows)
        med_struct=statistics.median(float(r[k_struct]) for r in rows)
        med_sum=statistics.median(float(r[k_sum]) for r in rows)
        print(f'rate_{rate}kbps median_s raw={med_raw:.3f} structured={med_struct:.3f} summary={med_sum:.3f}')
    print()

summarize('experiments/downlink_payload/results/downlink_metrics_20.csv', '20-images')
summarize('experiments/downlink_payload/results/downlink_metrics_100.csv', '100-images')

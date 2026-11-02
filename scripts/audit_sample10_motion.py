"""Measure localized changes missed by the current global freeze threshold; never rescore."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np


def longest_run(values):
    longest = current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    results = []
    for case in json.loads(args.cases.read_text()):
        if case['status'] != 'ok':
            continue
        capture = cv2.VideoCapture(case['video_path'])
        fps = capture.get(cv2.CAP_PROP_FPS)
        previous = None
        means, fractions = [], []
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frame = cv2.resize(frame, (256, 144), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if previous is not None:
                delta = cv2.absdiff(gray, previous)
                means.append(float(delta.mean()) / 255)
                fractions.append(float(np.mean(delta >= 16)))
            previous = gray
        capture.release()
        assert len(means) == 74 and fps == 15, case['id']
        global_low = [mean < 0.002 for mean in means]
        localized = [fraction >= 0.001 for fraction in fractions]
        # A diagnostic only: >=0.1% pixels differ by >=16 gray levels.
        # This is not an alternative acceptance threshold.
        results.append(dict(id=case['id'], adjacent_pairs=len(means),
            global_low_motion_pairs=sum(global_low),
            localized_change_pairs=sum(localized),
            localized_change_pairs_classified_low_motion=sum(a and b for a, b in zip(global_low, localized)),
            current_freeze_seconds=round(longest_run(global_low) / fps, 4),
            mean_gray_differences=means, fraction_pixels_gray_difference_ge16=fractions))
    args.out.write_text(json.dumps(dict(
        interpretation='Diagnostic of global-mean dilution only; no acceptance threshold or original score changed.',
        operator_resolution=[256, 144],
        localized_change_definition='at least 0.1% pixels differ by at least 16 gray levels between adjacent decoded frames at operator resolution',
        cases=results), ensure_ascii=False, indent=2) + '\n')
    for row in results:
        print(row['id'], row['current_freeze_seconds'], row['localized_change_pairs_classified_low_motion'])


if __name__ == '__main__':
    main()

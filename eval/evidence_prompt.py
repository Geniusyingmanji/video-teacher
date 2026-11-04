"""Lossless table encoding of repeated evidence fields in judge prompts."""
import json


def prompt_json(value):
    def compact(item):
        if isinstance(item, dict):
            return {key: table(val) if key == 'requirement_evidence' else compact(val)
                    for key, val in item.items()}
        if isinstance(item, list):
            return [compact(val) for val in item]
        return item

    def table(rows):
        if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
            return compact(rows)
        columns = list(rows[0])
        if any(set(row) != set(columns) for row in rows):
            return compact(rows)
        return {'columns': columns, 'rows': [[compact(row[key]) for key in columns] for row in rows]}

    return json.dumps(compact(value), ensure_ascii=False, separators=(',', ':'))

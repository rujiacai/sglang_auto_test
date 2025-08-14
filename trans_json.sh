#!/bin/bash
set -x
filename=$1
name_without_extension="${filename%.*}"
#name_without_extension=$(basename "$filename" ".jsonl")

jq -r 'to_entries | map(.value) | @csv' $name_without_extension.jsonl > $name_without_extension.csv
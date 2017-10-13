#!/bin/sh

if [ -z "$1" ]; then
   echo "provide the name of the backup folder"
   exit 0;
fi

mkdir backups/"$1"

BU=backups/"$1"/

cp -r logs $BU
rm -rf logs/*

cp AndroidAnalysis.log $BU
rm AndroidAnalysis.log

cp -r results $BU
rm -rf results/* 

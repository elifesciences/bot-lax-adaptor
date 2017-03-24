#!/bin/bash
# tests the guinea pigs articles with the new iiif schema

cd schema/api-raml
git fetch origin +refs/pull/*:refs/pull/* # download commits of PRs
cd -
./download-api-raml.sh refs/pull/122/head
cd schema/api-raml
npm install
node compile.js
cd -
./guinea-pigs.sh


# jats-scraper2

The next incarnation of the jats-scraper.

The previous jats-scraper was used to generate the 'EIF' json, used as convenient representation of a subset of article data derived from XML and non-XML sources.

This version of the jats-scraper is intended to:

* produce a complete representaion of a JATS XML article in JSON
* validate result against our evolving JSON Schema article specification
* report any/all problems in scraping

## installation

    $ ./install.sh

## usage

    $ source venv/bin/activate
    $ python src/main.py /path/to/a/jats.xml
    
Output at time of writing looks like:
    
    [
        {
            "article": {
                "impact-statement": "The bacterium <italic>Escherichia coli</italic> possesses a permissive cytoplasmic environment and the requisite molecular machinery to support the propagation of prions.", 
                "title": "Prion propagation can occur in a prokaryote and requires the ClpB chaperone"
            }, 
            "journal": {
                "id": 1, 
                "title": "eLife"
            }
        }
    ]

## Copyright & Licence

Copyright 2016 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

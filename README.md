# bot-lax-adaptor

This application:

1. listens for messages from the elife-bot
2. fetches remote xml
3. converts it to a partial representation of our article-json schema
4. sends data to Lax in an easily digestible format

## installation

    $ ./install.sh

## usage

    $ source venv/bin/activate
    $ python src/main.py /path/to/a/jats.xml
    
Output at time of writing looks like:
    
    [
        {
            "journal": {
                "id": "eLife", 
                "title": "eLife", 
                "issn": "2050-084X"
            }, 
            "article": {
                "id": "14107", 
                "version": null, 
                "type": "research-article", 
                "doi": "10.7554/eLife.14107", 
                "title": "Molecular basis for multimerization in the activation of the epidermal growth factor receptor", 
                "published": "2016-03-28T01:00:00", 
                "volume": 5, 
                "issue": null, 
                "elocationId": "e14107", 
                "copyright": {
                    "licence": "This article is distributed under the terms of the Creative Commons Attribution License, which permits unrestricted use and redistribution provided that the original author and source are credited.", 
                    "holder": "Huang et al"
                }, 
                "pdf": null, 
                "subjects": [
                    "biochemistry", 
                    "biophysics-structural-biology"
                ], 
                "research-organisms": [
                    "Human", 
                    "Xenopus"
                ], 
                "related-articles": [], 
                "abstract": {
                    "doi": "10.7554/eLife.14107.001", 
                    "content": "The epidermal growth factor receptor (EGFR) is activated by dimerization, but activation also generates higher-order multimers, whose nature and function are poorly understood. We have characterized ligand-induced dimerization and multimerization of EGFR using single-molecule analysis, and show that multimerization can be blocked by mutations in a specific region of Domain IV of the extracellular module. These mutations reduce autophosphorylation of the C-terminal tail of EGFR and attenuate phosphorylation of phosphatidyl inositol 3-kinase, which is recruited by EGFR. The catalytic activity of EGFR is switched on through allosteric activation of one kinase domain by another, and we show that if this is restricted to dimers, then sites in the tail that are proximal to the kinase domain are phosphorylated in only one subunit. We propose a structural model for EGFR multimerization through self-association of ligand-bound dimers, in which the majority of kinase domains are activated cooperatively, thereby boosting tail phosphorylation."
                }
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

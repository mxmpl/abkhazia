# Copyright 2016 Thomas Schatz, Xuan Nga Cao, Mathieu Bernard
#
# This file is part of abkhazia: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Abkhazia is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with abkhazia. If not, see <http://www.gnu.org/licenses/>.
"""Test of language modeling"""

import os
import pytest

import abkhazia.models.language_model as language_model
import abkhazia.utils as utils
from .conftest import assert_no_error_in_log


levels = ['phone', 'word']
orders = [1, 2, 3]
params = [(l, o) for l in levels for o in orders]


def test_word2phone(corpus):
    phones = language_model.word2phone(corpus)

    assert sorted(phones.keys()) == sorted(corpus.utts())
    assert len(phones) == len(corpus.text)


@pytest.mark.parametrize('level, order', params)
def test_lm(level, order, corpus, tmpdir):
    output_dir = str(tmpdir.mkdir('lang'))
    flog = os.path.join(output_dir, 'language.log')
    log = utils.get_log(flog)

    lm = language_model.LanguageModel(corpus, output_dir, log=log)
    lm.level = level
    lm.order = order
    lm.create()
    lm.run()
    lm.export()
    language_model.check_language_model(output_dir)
    assert_no_error_in_log(flog)

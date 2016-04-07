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
"""Provides the ForceAlign class"""

import os

from abkhazia.kaldi.kaldi_path import kaldi_path
import abkhazia.kaldi.abstract_recipe as abstract_recipe
import abkhazia.kaldi.kaldi2abkhazia as k2a
import abkhazia.utils as utils


class ForceAlign(abstract_recipe.AbstractRecipe):
    """Compute forced alignment of an abkhazia corpus

    Takes a corpus in abkhazia format and instantiates a kaldi recipe
    to train a standard speaker-adapted triphone HMM-GMM model on the
    whole corpus and generate a forced alignment.

    """
    name = 'align'

    def __init__(self, corpus_dir, recipe_dir=None, verbose=False, njobs=1):
        super(ForceAlign, self).__init__(corpus_dir, recipe_dir, verbose)
        self.njobs = njobs

        # language and acoustic models directories
        self.lm_dir = None
        self.am_dir = None

    @staticmethod
    def _check_template(param, name, target):
        if param is None:
            raise RuntimeError('non specified {} model'.format(name))
        if not os.path.isfile(target):
            raise RuntimeError('non valid {} model: {} not found'
                               .format(name, target))

    def _check_acoustic_model(self):
        self._check_template(
            self.am_dir, 'acoustic', os.path.join(self.am_dir, 'final.mdl'))

    def _check_language_model(self):
        self._check_template(
            self.lm_dir, 'language', os.path.join(self.lm_dir, 'phones.txt'))

    def _align_fmllr(self):
        target = os.path.join(self.recipe_dir, 'exp', 'ali_fmllr')
        self.log.info('computing forced alignment to %s', target)

        if not os.path.isdir(target):
            os.makedirs(target)

        command = (
            'steps/align_fmllr.sh --nj {0} --cmd "{1}" {2} {3} {4} {5}'
            .format(
                self.njobs,
                utils.config.get('kaldi', 'train-cmd'),
                os.path.join(self.recipe_dir, 'data', 'align'),
                self.lm_dir,
                self.am_dir,
                target))

        self.log.debug('running %s', command)
        utils.jobs.run(command, stdout=self.log.debug,
                       env=kaldi_path(), cwd=self.recipe_dir)

    def _ali_to_phones(self):
        export = os.path.join(self.recipe_dir, 'export')
        target = os.path.join(export, 'forced_alignment.tra')
        self.log.info('exporting results to %s', target)

        if not os.path.isdir(export):
            os.makedirs(export)

        command = (
            'ali-to-phones --write_lengths=true {0}'
            ' "ark,t:gunzip -c {1}|" ark,t:{2}'.format(
                os.path.join(self.am_dir, 'final.mdl'),
                os.path.join(self.recipe_dir, 'exp', 'ali_fmllr', 'ali.1.gz'),
                target))

        utils.jobs.run(command,
                       stdout=self.log.debug,
                       env=kaldi_path())

        # if we want to use the tri2a results directly without the final
        # forced alignment (is there any difference between the two beyond one
        # being done using only one job?)
        # ali-to-phones \
        #     --write_lengths=true exp/tri2a/final.mdl \
        #     "ark,t:gunzip -c exp/tri2a/ali.*.gz|" \
        #     ark,t:export/forced_alignment.tra

    def _export(self):
        """Export the kaldi tra alignment file in abkhazia format

        This method reads data/lang/phones.txt and
        export/forced_aligment.tra and write
        export/forced_aligment.txt

        """
        tra = os.path.join(self.recipe_dir, 'export', 'forced_alignment.tra')
        k2a.export_phone_alignment(
            os.path.join(self.lm_dir, 'phones.txt'),
            tra, tra.replace('.tra', '.txt'))

    def check_parameters(self):
        self._check_acoustic_model()
        self._check_language_model()

    def create(self):
        """Create the recipe data in `self.recipe_dir`"""
        self._check_acoustic_model()

        target_dir = os.path.join(self.recipe_dir, 'data/align')
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        # setup data files. Those files are linked from the acoustic
        # model dircetory instead of being prepared from the corpus
        # directory.
        for source in ('text', 'utt2spk', 'spk2utt', 'segments',
                       'wav.scp', 'feats.scp', 'cmvn.scp'):
            origin = os.path.abspath(os.path.join(
                self.am_dir, '../../data/acoustic', source))
            if os.path.isfile(origin):
                target = os.path.join(target_dir, source)
                if not os.path.isfile(target):
                    os.link(origin, target)
            else:
                self.log.debug('no such file %s', origin)

        # setup other files and folders
        self.a2k.setup_kaldi_folders()
        self.a2k.setup_machine_specific_scripts()

    def run(self):
        self.check_parameters()
        self._align_fmllr()
        self._ali_to_phones()
        self._export()

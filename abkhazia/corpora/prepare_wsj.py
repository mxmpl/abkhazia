#!/usr/bin/env python
# coding: utf-8
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
# along with abkahzia. If not, see <http://www.gnu.org/licenses/>.

"""Data preparation for the Wall Street Journal corpus

To prepare wav files, the executable 'sph2pipe' must be present on
your PATH.

"""

import os
import progressbar
import re

from abkhazia.corpora.utils import (
    AbstractPreparator,
    list_files_with_extension,
    list_directory,
    sph2wav,
    open_utf8,
    default_argument_parser
)


class WallStreetJournalPreparator(AbstractPreparator):
    """Convert the WSJ corpus to the abkhazia format"""

    name = 'WallStreetJournal'

    # IPA transcription of the CMU phones
    phones = {
        'IY': u'iː',
        'IH': u'ɪ',
        'EH': u'ɛ',
        'EY': u'eɪ',
        'AE': u'æ',
        'AA': u'ɑː',
        'AW': u'aʊ',
        'AY': u'aɪ',
        'AH': u'ʌ',
        'AO': u'ɔː',
        'OY': u'ɔɪ',
        'OW': u'oʊ',
        'UH': u'ʊ',
        'UW': u'uː',
        'ER': u'ɝ',
        'JH': u'ʤ',
        'CH': u'ʧ',
        'B': u'b',
        'D': u'd',
        'G': u'g',
        'P': u'p',
        'T': u't',
        'K': u'k',
        'S': u's',
        'SH': u'ʃ',
        'Z': u'z',
        'ZH': u'ʒ',
        'F': u'f',
        'TH': u'θ',
        'V': u'v',
        'DH': u'ð',
        'M': u'm',
        'N': u'n',
        'NG': u'ŋ',
        'L': u'l',
        'R': u'r',
        'W': u'w',
        'Y': u'j',
        'HH': u'h'
    }

    silences = [u"NSN"]  # SPN and SIL will be added automatically

    variants = []  # could use lexical stress variants...

    file_pattern = None

    directory_pattern = None

    @staticmethod
    def correct_word(word):
        """Return the word with a corrected formating

        Correct the formating of some word or return an empty string to
        indicate that the word should be ignored.

        The corrections applied are:

        * Upcase everything to match the CMU dictionary

        * Remove backslashes (as we don't need the quoting)

        * Normalization for Nov'93 test transcripts (%PERCENT ->
          PERCENT and .POINT -> POINT)

        * the <> means verbal deletion of a word, we just remove
          brackets

        * Other noise indications, e.g. [loud_breath].We replace them
          by the generic <NOISE> marker

        * Replace '--DASH' by '-DASH' to conform with the CMU
          dictionary

        The ignored words (returning an empty string) are:

        * '~' indicates the truncation of an utterance, not a word

        * '.' used to indicate a pause, not included in the transcript
          for now. (could use a special SIL word in the dictionary for
          this)

        * E.g. [<door_slam], this means a door slammed in the
          preceding word. We remove it from the transcript and keep
          the preceding word. (could replace the preceding word by
          <NOISE>)

        * E.g. [door_slam>], this means a door slammed in the next
          word. We remove it from the transcript and keep the next
          word. (could replace the next word by <NOISE>)

        * E.g. [phone_ring/], which indicates the start of this
          phenomenon. We remove it from the transcript and keep the
          part where the phone rings. (could replace the whole part
          where the phone rings by <NOISE>)

        * E.g. [/phone_ring], which indicates the end of this
          phenomenon. We remove it from the transcript and keep the
          part where the phone rings. (could replace the whole part
          where the phone rings by <NOISE>)

        """
        if word == '':
            return ''

        # correct word formating and ignore <> (means verbal deletion)
        word = word.upper()
        word = word.replace('\\', '')
        word = word.replace('%PERCENT', 'PERCENT').replace('.POINT', 'POINT')
        if word[0] == '<' and word[-1] == '>':
            word = word[1:-1]

        # ignore some words
        if(word == '~' or word == '.' or
           (word[:1] == '[<' and word[-1] == ']') or
           (word[0] == '[' and word[-2:] == '>]') or
           (word[0] == '[' and word[-2:] == '/]') or
           (word[:1] == '[/' and word[-1] == ']')):
            return ''

        # correct noise indications
        if word[0] == '[' and word[-1] == ']':
            return '<noise>'

        # This is a common issue; the CMU dictionary has it as -DASH.
        if word == '--DASH':
            return '-DASH'

        # if we reached this point without returning, return w as is
        return word

    def __init__(self, input_dir, cmu_dict,
                 output_dir=None, verbose=False):
        # call the AbstractPreparator __init__
        super(WallStreetJournalPreparator, self).__init__(
            input_dir, output_dir, verbose)

        # init path to the CMU dictionary
        if not os.path.isfile(cmu_dict):
            raise IOError(
                'CMU dictionary does not exist: {}'.format(cmu_dict))
        self.cmu_dict = cmu_dict

        # select only a subpart of recordings and transcriptions.
        # Listing files using the following 2 criterions: 1- files are
        # nested within self.directory_pattern and 2- the 4th letter
        # in the file name is self.file_pattern
        self.log.debug('directory pattern is {}, file pattern is {}'
                       .format(self.directory_pattern, self.file_pattern))

        if self.directory_pattern is None:
            dir_filter = lambda d: True
        else:
            dir_filter = lambda d: d in self.directory_pattern

        if self.file_pattern is None:
            filter_dot = lambda f: f[-4:] == '.dot'
            filter_wv1 = lambda f: f[-4:] == '.wv1'
        else:
            filter_dot = lambda f: (
                f[3] == self.file_pattern and f[-4:] == '.dot')
            filter_wv1 = lambda f: (
                f[3] == self.file_pattern and f[-4:] == '.wv1')

        self.input_recordings = self.list_files(dir_filter, filter_wv1)
        self.input_transcriptions = self.list_files(dir_filter, filter_dot)
        self.log.info('selected {} speech files and {} transcription files'
                      .format(len(self.input_recordings),
                              len(self.input_transcriptions)))

        # filter out the corrupted utterances from recordings. The tag
        # '[bad_recording]' in a transcript indicates a problem with
        # the associated recording (if it even exists) so exclude it
        self.bad_utts = []
        for trs in self.input_transcriptions:
            for line in open_utf8(trs, 'r').xreadlines():
                if '[bad_recording]' in line:
                    #print trs, line
                    utt_id = re.match(r'(.*) \((.*)\)', line).group(2)
                    self.bad_utts.append(utt_id)

        self.log.info('Found {} corrupted utterances'
                      .format(len(self.bad_utts)))

    def list_files(self, dir_filter, file_filter):
        """Return a list of abspaths to relevant WSJ files"""
        matched = []
        for path, dirs, _ in os.walk(self.input_dir):
            for d in (d for d in dirs if dir_filter(d)):
                for d_path, _, files in os.walk(os.path.join(path, d)):
                    matched += [os.path.join(d_path, f)
                                for f in files if file_filter(f)]
        return matched

    def make_wavs(self):
        self.log.info('converting {} sph files to wav...'
                      .format(len(self.input_recordings)))

        for sph in progressbar.ProgressBar()(self.input_recordings):
            utt_id = os.path.basename(sph).replace('.wv1', '')
            if utt_id not in self.bad_utts:  # exclude some utterances
                wav = os.path.join(self.wavs_dir, utt_id + '.wav')
                if not os.path.exists(wav):
                    sph2wav(sph, wav)

        self.log.debug('converted all files to wav')

    def make_segment(self):
        with open_utf8(self.segments_file, 'w') as out:
            for wav in list_directory(self.wavs_dir):
                utt_id = os.path.basename(wav).replace('.wav', '')
                out.write(u"{0} {1}\n".format(utt_id, wav))
        self.log.debug('finished creating segments file')

    def make_speaker(self):
        with open_utf8(self.speaker_file, 'w') as out:
            for wav in list_directory(self.wavs_dir):
                utt_id = os.path.basename(wav).replace('.wav', '')
                # speaker_id are the first 3 characters of the filename
                out.write(u"{0} {1}\n".format(utt_id, utt_id[:3]))
        self.log.debug('finished creating utt2spk file')

    def make_transcription(self):
        # concatenate all the transcription files
        transcription = []
        for trs in self.input_transcriptions:
            transcription += open_utf8(trs, 'r').readlines()

        # parse each line and write it to output file in abkhazia format
        with open_utf8(self.transcription_file, 'w') as out:
            for line in transcription:
                # parse utt_id and text
                matches = re.match(r'(.*) \((.*)\)', line.strip())
                text = matches.group(1)
                utt_id = matches.group(2)

                # skip bad utterances
                if utt_id not in self.bad_utts:
                    # TODO is it still required ? correct some defect
                    # in original corpus (ad hoc)
                    # if utt_id == '400c0i2j':
                    #     text = text.replace('  ', ' ')

                    # re-format text and remove empty words
                    words = [self.correct_word(w) for w in text.split(' ')]
                    text = ' '.join([w for w in words if w != ''])

                    # output to file
                    out.write(u"{0} {1}\n".format(utt_id, text))

        self.log.debug('finished creating text file')

    def make_lexicon(self):
        with open_utf8(self.lexicon_file, 'w') as out:
            for line in open_utf8(self.cmu_dict, 'r').readlines():
                # remove newline and trailing spaces
                line = line.strip()

                # skip comments
                if not (len(line) >= 3 and line[:3] == u';;;'):
                    # parse line
                    word, phones = line.split(u'  ')

                    # skip alternative pronunciations, the first one
                    # (with no parenthesized number at the end) is
                    # supposed to be the most common and is retained
                    if not re.match(ur'(.*)\([0-9]+\)$', word):
                        # ignore stress variants of phones
                        phones = re.sub(u'[0-9]+', u'', phones)
                        # write to output file
                        out.write(u"{0} {1}\n".format(word, phones))

            # add special word: <noise> NSN. special word <unk> SPN
            # will be added automatically during corpus validation but
            # it would make sense if to add it here if we used it for
            # some particular kind of noise, but this is not the case
            # at present
            out.write(u"<noise> NSN\n")
        self.log.debug('finished creating lexicon file')


# TODO check if that's correct (in particular no sd_tr_s or l in WSJ1
# and no si_tr_l in WSJ0 ??)

class JournalistReadPreparator(WallStreetJournalPreparator):
    """Prepare only the journalist read speech from WSJ

    The selected directory pattern is 'si_tr_j' and file pattern is 'c'

    si = speaker-independent (vs sd = speaker-dependent)
    tr = training data
    j = journalist read
    c = common read speech (as opposed to spontaneous, adaptation read)

    """
    name = WallStreetJournalPreparator.name + '-journalist-read'
    dir_pattern = ['si_tr_j']
    file_pattern = 'c'


class JournalistSpontaneousPreparator(WallStreetJournalPreparator):
    """Prepare only the journalist sponaneous speech from WSJ

    The selected directory pattern is 'si_tr_j' and file pattern is 's'

    si = speaker-independent
    tr = training data
    jd = spontaneous journalist dictation
    s = spontaneous no/unspecified verbal punctuation (as opposed to
      common read speech, adaptation read)

    """
    name = WallStreetJournalPreparator.name + '-journalist-spontaneous'
    directory_pattern = ['si_tr_jd']
    file_pattern = 's'


class MainReadPreparator(WallStreetJournalPreparator):
    """Prepare only the read speech from WSJ

    The selected directory pattern are 'si_tr_s', 'si_tr_l',
    'sd_tr_s', 'sd_tr_l' and file pattern is 'c'

    si = speaker-independent
    sd = speaker-dependent
    tr = training data
    s = standard subjects need to read approximately 260 sentences
    l = long sample with more than 1800 read sentences
    c = common read speech as opposed to spontaneous, adaptation read

    """
    name = WallStreetJournalPreparator.name + '-main-read'
    directory_pattern = ['si_tr_s', 'si_tr_l', 'sd_tr_s', 'sd_tr_l']
    file_pattern = 'c'


# To deal with specific WSJ command line arguments, we can't use the
# default corpora.utils.main function
def main():
    """The command line entry for WSJ corpus preparation"""
    try:
        # mapping of the three WSJ variations
        selection = [
            ('journalist-read', JournalistReadPreparator),
            ('journalist-spontaneous', JournalistSpontaneousPreparator),
            ('main-read', MainReadPreparator)
        ]

        selection_descr = ', '.join([str(i+1) + ' is ' + selection[i][0]
                                     for i in range(len(selection))])

        # add WSJ specific arguments to the parser
        parser = default_argument_parser(
            WallStreetJournalPreparator.name, __doc__)

        parser.add_argument('-s', '--selection', default=None,
                            metavar='SELECTION', type=int,
                            choices=range(1, len(selection)+1),
                            help='the subpart of WSJ to prepare. If not '
                            'specified, prepare the entire corpus. '
                            'Choose SELECTION in {}. ('
                            .format(range(1, len(selection)+1))
                            + selection_descr + ')')

        parser.add_argument('cmu_dict', help='the CMU dictionary '
                            'file to use for lexicon generation')

        # parse command line arguments
        args = parser.parse_args()

        # select the preparator
        preparator = (WallStreetJournalPreparator if args.selection is None
                      else selection[args.selection-1][1])

        # prepare the corpus
        corpus_prep = preparator(args.input_dir, args.cmu_dict,
                                 args.output_dir, args.verbose)

        corpus_prep.prepare()
        if not args.no_validation:
            corpus_prep.validate()

    except Exception as err:
        print('fatal error: {}'.format(err))

if __name__ == '__main__':
    main()
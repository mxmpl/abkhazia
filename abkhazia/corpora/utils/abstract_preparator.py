"""Provides a base class for corpora preparation in the abkhazia format"""

import codecs
import os
import shutil

from abkhazia.corpora.utils import validation
from abkhazia.corpora.utils import DEFAULT_OUTPUT_DIR
from abkhazia.utilities.log2file import get_log

class AbstractPreparator(object):
    """This class is a common wrapper to all the corpus preparators

    The AbstractPreparator provides the basic functionalities all
    corpus preparators rely on for the conversion of a specific corpus
    to the abkhazia format. Moreover it proposes a set of abstract
    methods that each specialized prepartor must implement. Those
    methods correspond to the corpus preparation steps.

    Parameters
    ----------

    The following parameters are specified when initializing a new
    preparator.

    'input_dir' : The input directory containing the raw distribution
        of the corpus to prepare. This directory must exists on the
        filesystem.

    'output_dir' : The output directory where to write the prepared
        version of the corpus. If not specified, a default directory
        is guessed based on the corpus name.

    'verbose' : This argument serves as initialization of the log2file
        module. See there for more doc.

    'overwrite' : If True, delete any content on 'output_dir' during
        initialization. If False and if 'output_dir' exists, the
        initialization fails and raises an exception.

    Methods
    -------

    From a user persepctive, the most important methods offered by the
    abstract preparator are prepare() and validate(). See there
    documentation for more details.

    In order to specialize the preparator to a new corpus, the
    following variables must be defined and following methods must be
    implemented

    TODO

    For more details on data preparation, please refer to
    https://github.com/bootphon/abkhazia/wiki/data_preparation

    """
    def __init__(self, input_dir, output_dir=None,
                 verbose=False, overwrite=False):
        self.verbose = verbose

        # init input directory
        if not os.path.isdir(input_dir):
            raise IOError(
                'input directory does not exist:\n{}'.format(input_dir))
        self.input_dir = os.path.abspath(input_dir)

        # init output directory
        if output_dir is None:
            self.output_dir = os.path.join(DEFAULT_OUTPUT_DIR, self.name)
        else:
            self.output_dir = os.path.abspath(output_dir)

        # check if output directory already exists
        if overwrite:
            shutil.rmtree(self.output_dir)
        elif os.path.exists(self.output_dir):
            raise IOError(
                'output directory already exists:\n{}'.format(self.output_dir))

        # create empty hierarchy output_dir/data/wavs
        self.data_dir = os.path.join(self.output_dir, 'data')
        self.wavs_dir = os.path.join(self.data_dir, 'wavs')
        os.makedirs(self.wavs_dir)

        # init output files that will be populated by prepare()
        fname = lambda name: os.path.join(self.data_dir, name)
        self.segments_file = fname('segments.txt')
        self.speaker_file = fname('utt2spk.txt')
        self.transcription_file = fname('text.txt')
        self.lexicon_file = fname('lexicon.txt')
        self.phones_file = fname('phones.txt')
        self.variants_file = fname('variants.txt')
        self.silences_file = fname('silences.txt')

        # create the log dir if not existing
        self.logs_dir = os.path.join(self.output_dir, 'logs')
        os.makedirs(self.logs_dir)

        # init the log with the log2file module
        self.log = get_log(os.path.join(self.logs_dir, 'data_preparation.log'),
                           self.verbose)
        self.log.info('{} preparator created, read from {}'
                      .format(self.name, self.input_dir))

    def prepare(self):
        """Prepare the corpus from raw distribution to abkhazia format"""
        self.log.info('preparing the {} corpus, writing to {}'
                      .format(self.name, self.data_dir))
        steps = [
            (self.link_wavs, self.wavs_dir),
            (self.make_segment, self.segments_file),
            (self.make_speaker, self.speaker_file),
            (self.make_transcription, self.transcription_file),
            (self.make_lexicon, self.lexicon_file),
            (self.make_phones, self.phones_file)
        ]
        for step, target in steps:
            self.log.info('writing {}'.format(os.path.basename(target)))
            step()

    def validate(self):
        """TODO document"""
        self.log.info('validating the prepared {} corpus'.format(self.name))
        validation.validate(self.output_dir, self.verbose)

    def make_phones(self):
        """Create phones, silences and variants list files

        The phone inventory contains a list of each symbol used in the
        pronunciation dictionary.

        The silences inventory contains a list of each symbol used to
        represent a silence.

        The variants inventory contains TODO

        phones.txt: <phone-symbol> <ipa-symbol>

        """
        open_utf8 = lambda f: codecs.open(f, mode='w', encoding='UTF-8')

        with open_utf8(self.phones_file) as out:
            for phone in self.phones:
                out.write(u'{0} {1}\n'.format(phone, self.phones[phone]))

        if self.silences is not []:
            with open_utf8(self.silences_file) as out:
                for sil in self.silences:
                    out.write(sil + u"\n")

        if self.variants is not []:
            with open_utf8(self.variants_file) as out:
                for var in self.variants:
                    out.write(u" ".join(var) + u"\n")

        self.log.debug(
            'finished creating phones.txt, silences.txt, variants.txt')


    ############################################
    #
    # The above functions are abstracts and must be implemented by
    # child classes for each supported corpus.
    #
    ############################################

    name = ''
    """The name of the corpus"""

    phones = {}
    """A dict associating each phone in corpus with it's pronunciation"""

    silences = []
    """TODO document"""

    variants = []
    """TODO document"""

    def link_wavs(self):
        """Links the corpus speech folder to the output directory

        Populate self.wavs_dir with symbolic links to the corpus
        speech files. Optionnaly rename them.

        """
        raise NotImplementedError

    def make_segment(self):
        """Create utterance file

        Populate self.segments_file with the list of all utterances
        with the name of the associated wavefiles.

        If there is more than one utterance per file, the start and
        end of the utterance in that wavefile expressed in seconds.

        segments.txt: <utterance-id> <wav-file> [<segment-begin> <segment-end>]

        """
        raise NotImplementedError

    def make_speaker(self):
        """Create speaker file

        Populate self.speaker_file with the list of all utterances
        with a unique identifier for the associated speaker.

        utt2spk.txt: <utterance-id> <speaker-id>

        """
        raise NotImplementedError

    def make_transcription(self):
        """Create transcription file

        Populate self.transcription_file with the transcription in
        word units for each utterance

        text.txt: <utterance-id> <word1> <word2> ... <wordn>

        """
        raise NotImplementedError

    def make_lexicon(self):
        """Create phonetic dictionary file

        The phonetic dictionary contains a list of words with their
        phonetic transcription

        lexicon.txt: <word> <phone_1> <phone_2> ... <phone_n>

        """
        raise NotImplementedError

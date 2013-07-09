"""
This module provides a basic class for reading in a simple spreadsheet (delimited text file) for concepts and words in a set of languages.
"""

__author__="Steven Moran"
__date__="2013-04"


import sys 
import unicodedata
from time import gmtime, strftime
from datetime import date,datetime

from ..sequence.ngram import *
from ..read.csv import *
from ..convert.csv import wl2csv

class Spreadsheet:
    """
    Basic class for reading spreadsheet data that has been outputted into a deliminted format, e.g. tab.

    # workflow

    0. dump to delimited format
    1. csv2list(fileformat)
    2. pass this module arguments (header:linenumber, data:rownumber, default 0:ids, 1:concepts, 2-n:languages)
    2. col and row names (range or integer) - can tell the number of languages and concepts, etc.
    2. irrelevant order (loop over the dictionary and use alias dictionary; doculect / language / )
    2. header
    2. spreadsheet.rc **keywords, use aliases
    x. define for the output - keyword for output e.g. full rows, or rows >= n, also have to define what we have; want specific languages, specific cognate IDs
    x. black list parsing (no empty cells, etc.)
    x. separator for multientries for keywords in the output as "," as default, etc. (list of separators)
    x. parse as a list and do a type check
    x. then flip into harry potter format
    x. then flip into wordlist format
    x. then add tokenization / orthographic parsing

    # add stats to harry potter output
    
    NAME_LNG : language name, NAME is the doculect-identifier
    CONCEPT : header for concepts

    Note that case is not important, you should "lower" each string before
    parsing in order to prevent confusion (that's what I do for Wordlist)

    Standard-Separator for Language-Columns: ";"

    well, that's for the moment, there will be surely more later on...

    """
    def __init__(self, 
                 filename,
                 fileformat = None, # ? what do you need this for? req'd in read.csv
                 dtype = None, # flag for different datatypes; required in read.csv 
                 comment = '#',
                 sep = '\t', # column separator
                 # header = 0, # row of the header
                 # concepts = 0, # column for the concepts
                 language_id = "NAME", # think about this variable name
                 meanings = "CONCEPT", # explicit name of column containing concepts
                 exclude_string = "!", #
                 # languages = [], # columns with language data -- TODO: must be ints
                 blacklist = "", # location of blacklist, think about start and end characters, etc. 
                 conf = "", # spreadsheet .rc file
                 cellsep = ';', # cell separator, separates forms in the same cell
                 verbose = False,
                 ):

        self.filename = filename
        self.fileformat = fileformat
        self.dtype = dtype
        self.comment = comment
        self.sep = sep
        # self.header = header
        # self.concepts = concepts
        self.language_id = language_id
        self.meanings = meanings
        # self.languages = languages
        self.blacklist = blacklist
        self.conf = conf
        self.cellsep = cellsep
        self.verbose = verbose

        self.matrix = []
        self._init_matrix()
        # Unicode NFD normalize the cell contents
        self._normalize()

        self._prepare()

        #for row in self.matrix:
        #    print(row)

    def _init_matrix(self):
        """
        Create a 2D array from the CSV input and Unicode normalize its contents
        """

        # TODO: check if spreadsheet is empty and throw error
        spreadsheet = csv2list(
            self.filename, 
            self.fileformat, 
            self.dtype, 
            self.comment, 
            self.sep
            )

        # columns that have language data
        language_indices = []

        # first row must be the header in the input; TODO: add more functionality
        header = spreadsheet[0] 
        for i in range(0, len(header)):
            header[i] = header[i].lower().strip()
            if header[i] == "concept":
                self.concepts = i
            if header[i].startswith(self.language_id.lower()):
                language_indices.append(i)

        matrix_header = []
        matrix_header.append(header[self.concepts])        
        for i in language_indices:
            matrix_header.append(header[i].replace("name", "").strip())
        self.matrix.append(matrix_header)

        # append the concepts and words in languages and append the rows
        for i in range(1, len(spreadsheet)): # skip the header row
            matrix_row = [] # collect concepts and languages to add to matrix
            temp = []
            for j in range(0, len(spreadsheet[i])):
                if j == self.concepts:
                    matrix_row.append(spreadsheet[i][j])
                if j in language_indices:
                    temp.append(spreadsheet[i][j])
            for item in temp:
                matrix_row.append(item)
            self.matrix.append(matrix_row)

        """
        n = self.header+1
        for i in range(self.header+1, len(self.spreadsheet)):
            # check for concept; if missing skip row
            if self.spreadsheet[i][self.concepts] == "":
                print("[i] Missing concept in row "+str(i)+". Skipping the row.")
                continue

            # print(str(n), len(self.spreadsheet[i]))
            # n += 1

            row = []
            row.append(self.spreadsheet[i][self.concepts])
            for language in self.languages:
                # print("row", str(len(self.spreadsheet[i])), self.spreadsheet[i])                
                row.append(self.spreadsheet[i][language])
            matrix.append(row)
            """

    def _normalize(self):
        """ 
        Function to Unicode normalize (NFD) cells in the matrix.
        """
        for i in range(0, len(self.matrix)):
            for j in range(0, len(self.matrix[i])):
                normalized_cell = unicodedata.normalize("NFD", self.matrix[i][j])
                if not normalized_cell == self.matrix[i][j]:
                    if self.verbose:
                        print("[i] Cell at <"+self.matrix[i][j]+"> ["+str(i)+","+str(j)+"] not in Unicode NFD. Normalizing.")
                    self.matrix[i][j] = normalized_cell
    
    def _prepare(self,full_rows = False):
        """
        Prepare the spreadsheet for automatic pass-on to Wordlist.
        """
        # we now assume that the matrix is 'normalized',i.e. that it only
        # contains concepts and counterparts, in later versions, we should make
        # this more flexible by adding, for example, also proto-forms, or
        # cognate ids

        # define a temporary matrix with full rows
        if not full_rows:
            matrix = self.matrix
        else:
            matrix = self.get_full_rows()

        # create the dictionary that stores all the data
        d = {}

        # iterate over the matrix
        idx = 1
        for i,line in enumerate(matrix[1:]):

            # get the concept
            concept = line[0]

            # get the rest
            for j,cell in enumerate(line[1:]):

                # get the language
                language = matrix[0][j+1]

                # get the counterparts
                counterparts = [x.strip() for x in cell.split(self.cellsep)]

                # append stuff to dictionary
                for counterpart in counterparts:
                    d[idx] = [concept,language,counterpart]
                    idx += 1
        # add the header to the dictionary
        d[0] = ["concept","doculect","counterpart"]

        # make the dictionary an attribute of spreadsheet
        self._data = dict([(k,v) for k,v in d.items() if k > 0])

        # make empty meta-attribute
        self._meta = dict(
                filename = self.filename
                )

        # make a simple header for wordlist import
        self.header = dict([(a,b) for a,b in zip(d[0],range(len(d[0])))])

    def get_full_rows(self):
        """
        Create a 2D matrix from only the full rows in the spreadsheet.
        """
        full_row_matrix = []

        for row in self.matrix:
            is_full = 1

            for token in row:
                if token == "":
                    is_full = 0

            if is_full:
                full_row_matrix.append(row)

        return(full_row_matrix)

    def print_doculect_character_counts(self, doculects=1):
        for i in range(0, len(self.matrix)):
            print(self.matrix[i])
            for j in range(doculects, len(self.matrix[i])):
                if not self.matrix[i][j] == "":
                    print(self.matrix[i][j])
                    

    def stats(self):
        """
        Convenience function to get some stats data about the spreadsheet
        """
        total_entries = 0
        entries = []
        header = self.matrix[0]
        total_cells = len(self.matrix)*len(header)

        for item in header:
            entries.append(0)

        for row in self.matrix:
            for i in range(0, len(row)):
                if not row[i] == "":
                    total_entries += 1
                    entries[i] = entries[i] + 1
        print()
        print("Simple matrix stats...")
        print()
        print("total rows in matrix:", len(self.matrix))
        print("total cols in matrix:", len(header))
        print("total possible cells:", total_cells)
        print("total filled cells  :", str(total_entries), "("+str((total_entries*1.0)/total_cells*100)[:4]+"%)")
        print()
        print("total cells per column:")
        for i in range(0, len(header)):
            print(header[i]+"\t"+str(entries[i]-1)) # do not include the header in count
        print()
    
    def pprint(self, delim="\t"):
        """
        Pretty print the matrix
        """
        for i in range(0, len(self.matrix)):
            row = ""
            for j in range(0, len(self.matrix[i])):
                row += self.matrix[i][j]+delim
            row = row.rstrip(delim)
            print(row)

    def print_qlc_format(self):
        """
        Print "simple" QLC format.
        """
        print("@input file: "+self.filename)
        print("@date: "+strftime("%Y-%m-%d %H:%M:%S", gmtime()))
        print("#")
        print("LANGUAGE"+"\t"+"CONCEPT"+"\t"+"COUNTERPART")

        id = 0
        for i in range(1, len(self.matrix)):
            for j in range(1, len(self.matrix[i])):
                id += 1
                if self.matrix[i][j] == "":
                    row = str(id)+"\t"+self.header[j]+"\t"+self.matrix[i][0]+"\t"+"NaN"
                else:
                    row = str(id)+"\t"+self.header[j]+"\t"+self.matrix[i][0]+"\t"+self.matrix[i][j]
                print(row)        

    def _output(self, fileformat, **keywords):
        """
        Output the matrix into Harry Potter format.
        """

        defaults = dict(
                filename = "lingpy-{0}".format(str(date.today())),
                meta = self._meta
                )
        for k in defaults:
            if k not in keywords:
                keywords[k] = defaults[k]
        
        # use wl2csv to convert if fileformat is 'qlc'
        if fileformat in ['qlc','csv']:
            wl2csv(
                    self.header,
                    self._data,
                    **keywords
                    )

    def output(
            self,
            fileformat,
            **keywords
            ):
        """
        Write Spreadsheet to different formats.
        """

        return self._output(fileformat,**keywords)

        #output = open(keywords['filename']+fileformat, "w")
        #output.write("ID"+"\t"+"CONCEPT"+"\t"+"COUNTERPART"+"\t"+"DOCULECT"+"\n")
        #header = self.matrix[0]
        #id = 0
        #for i in range(1, len(self.matrix)): # skip header row
        #    result = []
        #    concept = ""
        #    counterpart = ""
        #    doculect = ""

        #    for j in range(0, len(self.matrix[i])):
        #        cell = self.matrix[i][j]

        #        # identify the concept or counterpart
        #        if j == 0:
        #            concept = cell

        #        else:
        #            counterpart = cell
        #            doculect = header[j]

        #        if cell.__contains__(self.cellsep):
        #            tokens = cell.split(self.cellsep)
        #            for token in tokens:
        #                token = token.strip()
        #                id += 1
        #                result.append(str(id))
        #                result.append(concept)
        #                result.append(token)
        #                result.append(doculect)
        #                result.append(str(cogid))
        #                output.write("\t".join(result)+"\n")
        #                result = []
        #        else:
        #            if counterpart == "":
        #                continue
        #            id += 1
        #            result.append(str(id))
        #            result.append(concept)
        #            result.append(counterpart)
        #            result.append(doculect)
        #            result.append(str(cogid))
        #            output.write("\t".join(result)+"\n") 
        #            result = []
        #print()
        #print("[i] Writing matrix output to disk, filename:", filename)


"""
helpers.py: Static constants that are used
Same as those used in Jesse Steinweg-Woods' project
"""

PROG_LANG_KEYWORDS = ['R', 'Python', 'Java', 'C++', 'Ruby', 'Perl', 'Matlab', 'JavaScript', 'Scala']
ANALYSIS_TOOL_KEYWORDS = ['Excel', 'Tableau', 'D3.js', 'SAS', 'SPSS', 'D3']
HADOOP_KEYWORDS = ['Hadoop', 'MapReduce', 'Spark', 'Pig', 'Hive', 'Shark', 'Oozie', 'ZooKeeper', 'Flume', 'Mahout']
DATABASE_KEYWORDS = ['SQL', 'NoSQL', 'HBase', 'Cassandra', 'MongoDB']

DATA_SCI_KEYWORDS = PROG_LANG_KEYWORDS + ANALYSIS_TOOL_KEYWORDS + HADOOP_KEYWORDS + DATABASE_KEYWORDS

NA = 'NA'  # NaN value for city/state
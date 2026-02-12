#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Defines text replacement patterns as Python objects.
"""

import re
from typing import Dict, List, Union, Optional, Any


# Define pattern classes to represent different types of replacements

class SimplePattern:
    """Simple string-to-string replacement pattern."""

    def __init__(self, find: str, replace: str):
        """
        Initialize a simple replacement pattern.

        Args:
            find: String to find
            replace: String to replace with
        """
        self.find = find
        self.replace = replace

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format compatible with existing code."""
        return {self.find: self.replace}


class RegexPattern:
    """Regular expression based replacement pattern."""

    def __init__(self, regex: str, replace: str,
                 transform: Optional[str] = None,
                 transform_group: Optional[int] = None,
                 note: Optional[str] = None,
                 compile_regex: bool = True):
        """
        Initialize a regex replacement pattern.

        Args:
            regex: Regular expression pattern
            replace: Replacement string or template
            transform: Optional transformation to apply (e.g. 'uppercase')
            transform_group: Group number to apply transformation to
            note: Optional note about this pattern
            compile_regex: Whether to compile the regex for performance
        """
        self.regex = regex
        self.replace = replace
        self.transform = transform
        self.transform_group = transform_group
        self.note = note
        self.compiled_regex = re.compile(regex) if compile_regex else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format compatible with existing code."""
        pattern_dict = {"regex": self.regex, "replace": self.replace}
        if self.transform:
            pattern_dict["transform"] = self.transform
        if self.transform_group is not None:
            pattern_dict["transform_group"] = self.transform_group
        if self.note:
            pattern_dict["note"] = self.note
        return pattern_dict


class IncludePattern:
    """Meta-pattern that includes other pattern sets."""

    def __init__(self, pattern_names: List[str]):
        """
        Initialize a pattern inclusion directive.

        Args:
            pattern_names: List of pattern set names to include
        """
        self.pattern_names = pattern_names

    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary format compatible with existing code."""
        return {"include_patterns": self.pattern_names}


class PatternSet:
    """A set of related patterns with a name."""

    def __init__(self, name: str, patterns: List[Union[SimplePattern, RegexPattern, IncludePattern]]):
        """
        Initialize a pattern set.

        Args:
            name: Name of the pattern set
            patterns: List of patterns in this set
        """
        self.name = name
        self.patterns = patterns

    def to_list(self) -> List[Dict]:
        """Convert to list format compatible with existing code."""
        return [pattern.to_dict() for pattern in self.patterns]


# Define all pattern sets

# Standard cleanup patterns
consistent_ellipsis_patterns = [
    SimplePattern("...", "…"),
    SimplePattern("… ", "…"),
    SimplePattern(" …", "…"),
    SimplePattern("….", "…"),
    SimplePattern(".…", "…"),
    SimplePattern("……", "…"),
    SimplePattern("… ", "…")
]

strip_style_patterns = [
    RegexPattern(" style=\"font-weight:\\s*400;?\"", ""),
    RegexPattern(" style=\"(?!.*(?:font-weight|italic|bold|center|underline|line-through)).*\"", ""),
    RegexPattern("<span>((?:[^<]|<(?!/?span>))*)</span>", "\\1")
]

capitalize_start_of_tags_patterns = [
    RegexPattern(
        "<p([^>]*)>([\"“'‘]?)(\\.{3}|…)?([a-z])", "<p\\1>\\2\\3\\4",
        transform = "uppercase",
        transform_group = 4
    )
]

# Female to male conversion patterns
female_to_male_patterns = [
    SimplePattern("She ", "He "),
    SimplePattern(" she ", " he "),
    RegexPattern("She(['’, ])", "He\\1"),
    RegexPattern(" she(['’, ])", " he\\1"),
    SimplePattern("Herself", "Himself"),
    SimplePattern("herself", "himself"),
    SimplePattern("Her ", "His "),
    RegexPattern("Her['’]?s([.,!? ])", "His\\1"),
    RegexPattern(" her['’]?s([.,!? ])", " his\\1"),
    RegexPattern(" her([.,!?])", " him\\1"),
    RegexPattern(
        " her\\b(?= (a|all|about|above|across|after|again|against|along|amid|amidst|among|amongst|an|and|any|around|as|at|away|because|before|behind|being|below)\\b)",
        " him"),
    RegexPattern(
        " her\\b(?= (beneath|beside|besides|between|beyond|but|by|concerning|despite|down|during|either|even|except|for|from|if|in|inside)\\b)",
        " him"),
    RegexPattern(
        " her\\b(?= (into|like|myself|near|no|not|of|off|on|onto|or|out|over|past|per|plus|quite|regarding|since|so|some|something|such|than)\\b)",
        " him"),
    RegexPattern(
        " her\\b(?= (that|the|through|throughout|to|toward|towards|under|underneath|unlike|up|versus|what|when|while|with|within|without|would)\\b)",
        " him"),
    RegexPattern(" her\\b(?= (being|explain|feel|get|go|going|had|has|have|having|sit|want|wanted|was|were)\\b)", " him"),
    RegexPattern(" her\\b(?= (gently|quietly|roughly|sternly|sweetly|tightly)\\b)", " him"),
    RegexPattern(" her (\\w+)", " his \\1")
]

# British to American English
british_to_american_patterns = [
    SimplePattern("realise", "realize"),
    SimplePattern("analyse", "analyze"),
    SimplePattern("organise", "organize"),
    SimplePattern("recognise", "recognize"),
    SimplePattern("apologise", "apologize"),
    SimplePattern("colour", "color"),
    SimplePattern("favour", "favor"),
    SimplePattern("humour", "humor"),
    SimplePattern("neighbour", "neighbor"),
    SimplePattern("flavour", "flavor"),
    SimplePattern("centre", "center"),
    SimplePattern("metre", "meter"),
    SimplePattern("theatre", "theater"),
    SimplePattern("catalogue", "catalog"),
    SimplePattern("programme", "program"),
    SimplePattern("dialogue", "dialog"),
    SimplePattern("travelled", "traveled"),
    SimplePattern("travelling", "traveling"),
    SimplePattern("cancelled", "canceled"),
    SimplePattern("cancelling", "canceling"),
    SimplePattern("jewellery", "jewelry"),
    SimplePattern("pyjamas", "pajamas"),
    SimplePattern("grey", "gray"),
    SimplePattern("aeroplane", "airplane"),
    SimplePattern("aluminium", "aluminum"),
    SimplePattern("cheque", "check"),
    SimplePattern("speciality", "specialty"),
    SimplePattern("practise", "practice"),
    SimplePattern("defence", "defense"),
    SimplePattern("offence", "offense"),
    SimplePattern("draught", "draft"),
    SimplePattern("gaol", "jail"),
    SimplePattern("plough", "plow"),
    SimplePattern("sceptic", "skeptic")
]

# American to British English
american_to_british_patterns = [
    SimplePattern("realize", "realise"),
    SimplePattern("analyze", "analyse"),
    SimplePattern("organize", "organise"),
    SimplePattern("recognize", "recognise"),
    SimplePattern("apologize", "apologise"),
    SimplePattern("color", "colour"),
    SimplePattern("favor", "favour"),
    SimplePattern("humor", "humour"),
    SimplePattern("neighbor", "neighbour"),
    SimplePattern("flavor", "flavour"),
    SimplePattern("center", "centre"),
    SimplePattern("meter", "metre"),
    SimplePattern("theater", "theatre"),
    SimplePattern("catalog", "catalogue"),
    SimplePattern("program", "programme"),
    SimplePattern("dialog", "dialogue"),
    SimplePattern("traveled", "travelled"),
    SimplePattern("traveling", "travelling"),
    SimplePattern("canceled", "cancelled"),
    SimplePattern("canceling", "cancelling"),
    SimplePattern("jewelry", "jewellery"),
    SimplePattern("pajamas", "pyjamas"),
    SimplePattern("gray", "grey"),
    SimplePattern("airplane", "aeroplane"),
    SimplePattern("aluminum", "aluminium"),
    SimplePattern("check", "cheque"),
    SimplePattern("specialty", "speciality"),
    SimplePattern("practice", "practise"),
    SimplePattern("defense", "defence"),
    SimplePattern("offense", "offence"),
    SimplePattern("draft", "draught"),
    SimplePattern("jail", "gaol"),
    SimplePattern("plow", "plough"),
    SimplePattern("skeptic", "sceptic")
]

# Name normalization patterns
villain_remain_villain_patterns = [
    RegexPattern("Ra On|Ra-on|Ra-On|Laon|La On|La-on|La-On", "Raon"),
    RegexPattern("Hanlaon|Hallaon|Hanraon", "Han Raon"),
    RegexPattern("Shi(woo|-woo|-Woo| Woo|u)", "Siwoo"),
    RegexPattern("Si(-woo|-Woo| Woo|u)", "Siwoo"),
    RegexPattern("Siwooya", "Siwoo-ya"),
    RegexPattern("Ha Min|Ha-Min|Ha-min", "Hamin"),
    RegexPattern("Do(-jin|-Jin| Jin)", "Dojin"),
    RegexPattern("Tae(-geon|-Geon| Geon|gun|-gun|-Gun| Gun)", "Taegeon"),
    RegexPattern("Han(myung|-myung|-Myung|myeong|-myeong|-Myeong| Myeong)", "Han Myung",
note = "Company run by MC's father."),
RegexPattern("Myeong", "Myung"),
RegexPattern("Myung(-hoon|-Hoon| Hoon|hun|-hun|-Hun| Hun)", "Myunghoon",
note = "MC's father."),
RegexPattern("Han-Myung", "Han Myung"),
RegexPattern("Ju(won|-won|-Won| Won)", "Joowon"),
RegexPattern("Joo(-won|-Won| Won)", "Joowon"),
RegexPattern("Seok(hyeo|-Hyeo|-hyeo| Hyeo|-Hyu|-hyu| Hyu)n", "Seokhyun",
note = "Center Director.")
]



# Define all pattern sets
PATTERN_SETS = [
    PatternSet("standard-cleanup", [
        IncludePattern(["consistent-ellipsis", "strip-style", "capitalize-start-of-tags"])
    ]),
    PatternSet("consistent-ellipsis", consistent_ellipsis_patterns),
    PatternSet("strip-style", strip_style_patterns),
    PatternSet("capitalize-start-of-tags", capitalize_start_of_tags_patterns),
    PatternSet("female-to-male", female_to_male_patterns),
    PatternSet("british-to-american", british_to_american_patterns),
    PatternSet("american-to-british", american_to_british_patterns),
]

# Create a dictionary of pattern sets for easy lookup
PATTERNS = {pattern_set.name: pattern_set.to_list() for pattern_set in PATTERN_SETS}


def get_patterns() -> Dict[str, List[Dict]]:
    """
    Get all patterns in a format compatible with the existing code.

    Returns:
        Dictionary mapping pattern names to lists of pattern dictionaries
    """
    return PATTERNS
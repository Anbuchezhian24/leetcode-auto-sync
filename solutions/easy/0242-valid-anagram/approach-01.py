# LeetCode: Valid Anagram
# Problem ID: 0242
# Difficulty: Easy
# Language: python
# Approach: 01
# Submission ID: 2118654165
class Solution(object):
    def isAnagram(self, s, t):
        if len(s)!=len(t):
            return False
        else:
            for i in range(len(s)):
                if s.count(s[i])!=t.count(s[i]):
                    return False
            return True
        
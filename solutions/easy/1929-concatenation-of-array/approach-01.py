# LeetCode: Concatenation of Array
# Problem ID: 1929
# Difficulty: Easy
# Language: python
# Approach: 01
# Submission ID: 2083543384
class Solution(object):
    def getConcatenation(self, nums):
        ans=[]
        a=[]
        for i in nums:
            a.append(i)
        ans=a+nums
        return ans
            
        
# LeetCode: Plus One
# Problem ID: 0066
# Difficulty: Easy
# Language: python
# Approach: 01
# Submission ID: 2123155224
class Solution(object):
    def plusOne(self, digits):
        """
        :type digits: List[int]
        :rtype: List[int]
        """
        for i in range(len(digits)-1,-1,-1):
            if digits[i] ==9:
                digits[i]=0
            else:
                digits[i] = digits[i]+1
                return digits
        return [1]+digits
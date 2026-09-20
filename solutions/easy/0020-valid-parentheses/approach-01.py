# LeetCode: Valid Parentheses
# Problem ID: 0020
# Difficulty: Easy
# Language: python3
# Approach: 01
# Submission ID: 2137559916
class Solution:
    def isValid(self, s: str) -> bool:
        mapping = {')': '(', '}': '{', ']': '['}
        stack = []

        for char in s:
            if char in mapping.values():
                stack.append(char)
            elif char in mapping:
                if not stack or mapping[char] != stack.pop():
                    return False
        return not stack
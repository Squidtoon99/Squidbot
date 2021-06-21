import locale
import math
import operator
import traceback

from discord import Color, Embed
from discord.ext.commands import Cog
from ink.core import squidcommand
from pyparsing import (
    CaselessLiteral,
    Forward,
    Group,
    Literal,
    Optional,
    Word,
    ZeroOrMore,
    alphas,
    nums,
    oneOf,
)

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


class NumericStringParser(object):
    """
    Most of this code comes from the fourFn.py pyparsing example
    """

    def pushFirst(self, strg, loc, toks):
        self.exprStack.append(toks[0])

    def pushUMinus(self, strg, loc, toks):
        if toks and toks[0] == "-":
            self.exprStack.append("unary -")

    def __init__(self):
        """
        expop   :: '^'
        multop  :: '*' | '/'
        addop   :: '+' | '-'
        integer :: ['+' | '-'] '0'..'9'+
        atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'
        factor  :: atom [ expop factor ]*
        term    :: factor [ multop factor ]*
        expr    :: term [ addop term ]*
        """
        e = CaselessLiteral("E")
        fnumber = Word(
            nums + ",.kmbKMBe",
        )
        fnumber.setParseAction(
            self.parse_num
        )  # custom parse action for some pretty cool stuff
        ident = Word(alphas, alphas + nums + "_$")
        mod = Literal("%")
        plus = Literal("+")
        minus = Literal("-")
        mult = Literal("*")
        iadd = Literal("+=")
        imult = Literal("*=")
        idiv = Literal("/=")
        isub = Literal("-=")
        div = Literal("/")
        lpar = Literal("(").suppress()
        rpar = Literal(")").suppress()
        addop = plus | minus
        multop = mult | div | mod
        iop = iadd | isub | imult | idiv
        expop = Literal("^")
        pi = CaselessLiteral("PI")
        expr = Forward()
        atom = (
            (
                Optional(oneOf("- +"))
                + (ident + lpar + expr + rpar | pi | e | fnumber).setParseAction(
                    self.pushFirst
                )
            )
            | Optional(oneOf("- +")) + Group(lpar + expr + rpar)
        ).setParseAction(self.pushUMinus)
        # by defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-right
        # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor << atom + ZeroOrMore((expop + factor).setParseAction(self.pushFirst))
        term = factor + ZeroOrMore((multop + factor).setParseAction(self.pushFirst))
        expr << term + ZeroOrMore((addop + term).setParseAction(self.pushFirst))
        final = expr + ZeroOrMore((iop + expr).setParseAction(self.pushFirst))
        # addop_term = ( addop + term ).setParseAction( self.pushFirst )
        # general_term = term + ZeroOrMore( addop_term ) | OneOrMore( addop_term)
        # expr <<  general_term
        self.bnf = final
        # map operator symbols to corresponding arithmetic operations
        epsilon = 1e-12
        self.opn = {
            "+": operator.add,
            "-": operator.sub,
            "+=": operator.iadd,
            "-=": operator.isub,
            "*": operator.mul,
            "*=": operator.imul,
            "/": operator.truediv,
            "/=": operator.itruediv,
            "^": operator.pow,
            "%": operator.mod,
        }
        self.fn = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "exp": math.exp,
            "!": math.factorial,
            "factorial": math.factorial,
            "abs": abs,
            "trunc": lambda a: int(a),
            "round": round,
            "sgn": lambda a: abs(a) > epsilon and ((a > 0) - (a < 0)) or 0,
            "log": lambda a: math.log(a, 10),
            "ln": math.log,
            "log2": math.log2,
            "sqrt": math.sqrt,
        }

    @staticmethod
    def parse_num(op):
        multi = 1
        if type(op) not in [float, str]:
            op = op[0]
        op = str(op)
        if not (multi_raw := op[-1].lower()).isdigit():
            if multi_raw == "k":
                multi = 1e3
            elif multi_raw == "m":
                multi = 1e6
            elif multi_raw == "b":
                multi = 1e9
            op = op[:-1]

        return locale.atof(op) * multi

    def evaluateStack(self, s):
        op = s.pop()
        if op == "unary -":
            return -self.evaluateStack(s)
        if op in self.opn:
            op2 = self.evaluateStack(s)
            op1 = self.evaluateStack(s)
            return self.opn[op](op1, op2)
        elif op == "PI":
            return math.pi  # 3.1415926535
        elif op == "E":
            return math.e  # 2.718281828
        elif op in self.fn:
            return self.fn[op](self.evaluateStack(s))
        elif str(op).isalpha():
            return 0
        else:
            return self.parse_num(op)

    def eval(self, num_string, parseAll=True):
        self.exprStack = []
        self.bnf.parseString(num_string, parseAll)
        val = self.evaluateStack(self.exprStack[:])
        return val


class MathSolving(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.parser = NumericStringParser()

    @squidcommand("math")
    async def math(self, ctx, *, equation):
        """
        Solve a math equation
        """
        try:
            res = self.parser.eval(equation.strip())
        except BaseException:
            traceback.print_exc()
            res = "I can't solve that"
        else:
            res = "Calculated: {0:,.2f}\nRaw: {0}".format(res)

        yield res

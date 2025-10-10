/**
 * @name PoC: flag any import statement
 * @description Triggers on any Python import ... or from ... import ... statement.
 * @kind problem
 * @problem.severity recommendation
 * @precision very-high
 * @id proxidize/poc-import-present
 */

import python

from Import i
select i, "PoC: found an 'import' statement."

union

from ImportFrom f
select f, "PoC: found a 'from ... import ...' statement."
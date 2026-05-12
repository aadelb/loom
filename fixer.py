import libcst as cst
from libcst import matchers as m
import sys
import glob

class RaiseTransformer(cst.CSTTransformer):
    def __init__(self, func_name: str):
        self.func_name = func_name
    
    def leave_Raise(self, original_node: cst.Raise, updated_node: cst.Raise) -> cst.BaseSmallStatement:
        ret_dict = cst.Dict(
            elements=[
                cst.DictElement(key=cst.SimpleString("'error'"), value=cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("e"))])),
                cst.DictElement(key=cst.SimpleString("'error_code'"), value=cst.SimpleString("'internal'")),
                cst.DictElement(key=cst.SimpleString("'source'"), value=cst.SimpleString(f"'{self.func_name}'")),
            ]
        )
        return cst.Return(value=ret_dict)

class QualityFixer(cst.CSTTransformer):
    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        # Fix 1: timeout=30.0 for httpx.AsyncClient or httpx.Client
        if m.matches(updated_node.func, m.Attribute(value=m.Name("httpx"), attr=m.Name("AsyncClient") | m.Name("Client"))):
            has_timeout = any(
                isinstance(arg.keyword, cst.Name) and arg.keyword.value == "timeout"
                for arg in updated_node.args
            )
            if not has_timeout:
                new_arg = cst.Arg(keyword=cst.Name("timeout"), value=cst.Float("30.0"))
                return updated_node.with_changes(args=list(updated_node.args) + [new_arg])
        
        # Fix 2: Wrap blocking calls in asyncio.to_thread
        # requests.get, requests.post, etc.
        if m.matches(updated_node.func, m.Attribute(value=m.Name("requests"))):
            to_thread = cst.Attribute(value=cst.Name("asyncio"), attr=cst.Name("to_thread"))
            new_args = [cst.Arg(value=updated_node.func)] + list(updated_node.args)
            new_call = cst.Call(func=to_thread, args=new_args)
            return cst.Await(expression=new_call)

        # time.sleep
        if m.matches(updated_node.func, m.Attribute(value=m.Name("time"), attr=m.Name("sleep"))):
            to_thread = cst.Attribute(value=cst.Name("asyncio"), attr=cst.Name("to_thread"))
            new_args = [cst.Arg(value=updated_node.func)] + list(updated_node.args)
            new_call = cst.Call(func=to_thread, args=new_args)
            return cst.Await(expression=new_call)

        # open().read()
        if m.matches(updated_node.func, m.Attribute(value=m.Call(func=m.Name("open")), attr=m.Name("read"))):
            to_thread = cst.Attribute(value=cst.Name("asyncio"), attr=cst.Name("to_thread"))
            lambda_func = cst.Lambda(params=cst.Parameters(), body=updated_node)
            new_call = cst.Call(func=to_thread, args=[cst.Arg(value=lambda_func)])
            return cst.Await(expression=new_call)

        return updated_node

    def leave_ExceptHandler(self, original_node: cst.ExceptHandler, updated_node: cst.ExceptHandler) -> cst.ExceptHandler:
        # Fix 3: bare except -> except Exception as e
        if updated_node.type is None:
            return updated_node.with_changes(
                type=cst.Name("Exception"),
                name=cst.AsName(name=cst.Name("e"))
            )
        return updated_node

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        # Store initial body for further modification
        new_body = list(updated_node.body.body)
        
        # Fix 5: URL validation
        has_url_param = any(param.name.value == "url" for param in updated_node.params.params)
        if has_url_param:
            import_stmt = cst.parse_statement("from loom.validators import validate_url")
            validate_call = cst.parse_statement("validate_url(url)")
            
            # Make sure we don't duplicate if already present
            body_str = "".join(str(s) for s in new_body)
            if "validate_url(url)" not in body_str:
                new_body = [import_stmt, validate_call] + new_body

        updated_func = updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))

        # Fix 6: Replace raise with return dict
        updated_func = updated_func.visit(RaiseTransformer(updated_func.name.value))

        # Fix 4: Add -> dict[str, Any] to research_*
        if updated_func.name.value.startswith("research_"):
            if updated_func.returns is None:
                # Ensure Any is available by checking if we need an import later, or just use dict[str, Any] assuming typing is okay
                # -> dict[str, Any]
                dict_type = cst.Subscript(
                    value=cst.Name("dict"),
                    slice=[
                        cst.SubscriptElement(slice=cst.Index(value=cst.Name("str"))),
                        cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))
                    ]
                )
                returns = cst.Annotation(annotation=dict_type)
                updated_func = updated_func.with_changes(returns=returns)

        return updated_func


files = [
    'src/loom/tools/academic_integrity.py',
    'src/loom/tools/access_tools.py',
    'src/loom/tools/adversarial_craft.py',
    'src/loom/tools/adversarial_debate_tool.py',
    'src/loom/tools/agent_benchmark.py',
    'src/loom/tools/ai_safety.py',
    'src/loom/tools/ai_safety_extended.py',
    'src/loom/tools/anomaly_detector.py',
    'src/loom/tools/antiforensics.py',
    'src/loom/tools/api_fuzzer.py',
    'src/loom/tools/api_version.py',
    'src/loom/tools/arxiv_pipeline.py',
    'src/loom/tools/ask_all_models.py',
    'src/loom/tools/attack_economy.py',
    'src/loom/tools/attack_scorer.py',
    'src/loom/tools/audit_log.py',
    'src/loom/tools/audit_query.py',
    'src/loom/tools/auto_docs.py',
    'src/loom/tools/auto_experiment.py',
    'src/loom/tools/auto_params.py'
]

for fpath in files:
    try:
        with open(fpath, "r") as f:
            source = f.read()
        
        module = cst.parse_module(source)
        modified_module = module.visit(QualityFixer())
        
        with open(fpath, "w") as f:
            f.write(modified_module.code)
        
        print(f"Processed {fpath}")
    except Exception as e:
        print(f"Error in {fpath}: {e}")

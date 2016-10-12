import java.util.HashMap;
import java.io.InputStreamReader;

import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;
import com.google.gson.Gson;

public class VBA implements ParseTreeVisitor<String> {

	private Vocabulary voc;
	private String[] rules;
	private Gson gson;

	public VBA(vbaParser parser) {
		this.voc = parser.getVocabulary();
		this.rules = parser.getRuleNames();
		this.gson = new Gson();
	}

	@Override
	public String visit(ParseTree tree) {
		return tree.accept(this);
	}

	@Override
	public String visitChildren(RuleNode node) {
		String name = this.rules[node.getRuleContext().getRuleIndex()];
		String content = "{ \"name\": " + gson.toJson(name);
		int n = node.getChildCount();
		if (n == 0) {
			return content + "}";
		}
		String children = "";
		for (int i=0; i<n; i++) {
			ParseTree child = node.getChild(i);
                        if (children != "") {
				children = children + "," + child.accept(this);
			} else {
				children = child.accept(this);
			}
		}
		return content + ", \"children\": [" + children + "]}";
	}

	@Override
	public String visitTerminal(TerminalNode node) {
		HashMap<String, String> content = new HashMap<String, String>();
		try {
			content.put("name", this.voc.getDisplayName(node.getSymbol().getType()));
		} catch (IndexOutOfBoundsException e) {
			if (node.getSymbol().getType() == 1) {
				content.put("name", "EOF");
			} else {
				content.put("name", "Unknown (" + node.getSymbol().getType() + ")");
			}
		}
		content.put("value", node.getSymbol().getText());
		return gson.toJson(content);
	}

	@Override
	public String visitErrorNode(ErrorNode node) {
		System.out.println("ERROR");
		return "";
	}

	public static void main( String[] args) throws Exception {
		vbaLexer lexer;
		if (args.length > 0) {
			lexer = new vbaLexer(new ANTLRFileStream(args[0]));
		} else {
			lexer = new vbaLexer(new ANTLRInputStream(new InputStreamReader(System.in)));
		}
		CommonTokenStream tokens = new CommonTokenStream( lexer );
		vbaParser parser = new vbaParser( tokens );
		ParseTree tree = parser.startRule();
                System.out.println(new VBA(parser).visit(tree));
	}
}

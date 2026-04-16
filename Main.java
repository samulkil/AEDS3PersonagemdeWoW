import java.util.Scanner;
import java.util.Random;

public class Main {
    //Pega a letra e somo com a letra correspondente 
    public static String alterar(String texto, char a, char b) {
        String resultado = "";

        for (int i = 0; i < texto.length(); i++) {
            char c = texto.charAt(i);

            if (c == a) {
                resultado = resultado + b;
            } else {
                resultado = resultado + c;
            }
        }

        return resultado;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        Random gerador = new Random();
        gerador.setSeed(4);

        while (true) {
            String linha = sc.nextLine();

            if (linha.equals("FIM")) {
                break;
            }

            // Sorteia duas letras minúsculas
            char letra1 = (char) ('a' + (Math.abs(gerador.nextInt()) % 26));
            char letra2 = (char) ('a' + (Math.abs(gerador.nextInt()) % 26));

            String resultado = alterar(linha, letra1, letra2);
            System.out.println(resultado);
        }

        sc.close();
    }
}
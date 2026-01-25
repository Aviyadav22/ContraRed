/* eslint-disable @typescript-eslint/no-var-requires */

const devCerts = require("office-addin-dev-certs");
const CopyWebpackPlugin = require("copy-webpack-plugin");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const path = require("path");

async function getHttpsOptions() {
    const httpsOptions = await devCerts.getHttpsServerOptions();
    return { ca: httpsOptions.ca, key: httpsOptions.key, cert: httpsOptions.cert };
}

module.exports = async (env, options) => {
    const dev = options.mode === "development";

    const config = {
        devtool: "source-map",
        entry: {
            taskpane: ["./src/taskpane/taskpane.ts", "./src/taskpane/taskpane.html"],
        },
        output: {
            path: path.resolve(__dirname, "dist"),
            filename: "[name].js",
            clean: true,
        },
        resolve: {
            extensions: [".ts", ".tsx", ".html", ".js"],
        },
        module: {
            rules: [
                {
                    test: /\.ts$/,
                    exclude: /node_modules/,
                    use: "ts-loader",
                },
                {
                    test: /\.html$/,
                    exclude: /node_modules/,
                    use: "html-loader",
                },
                {
                    test: /\.css$/,
                    use: ["style-loader", "css-loader"],
                },
                {
                    test: /\.(png|jpg|jpeg|gif|ico)$/,
                    type: "asset/resource",
                    generator: {
                        filename: "assets/[name][ext]",
                    },
                },
            ],
        },
        plugins: [
            new HtmlWebpackPlugin({
                filename: "taskpane.html",
                template: "./src/taskpane/taskpane.html",
                chunks: ["taskpane"],
            }),
            new CopyWebpackPlugin({
                patterns: [
                    {
                        from: "assets/*",
                        to: "assets/[name][ext]",
                        noErrorOnMissing: true,
                    },
                    {
                        from: "manifest*.xml",
                        to: "[name][ext]",
                    },
                ],
            }),
        ],
        devServer: {
            headers: {
                "Access-Control-Allow-Origin": "*",
            },
            server: {
                type: "https",
                options: env.WEBPACK_BUILD || !dev ? {} : await getHttpsOptions(),
            },
            port: 3000,
            static: {
                directory: path.join(__dirname, "dist"),
            },
        },
    };

    return config;
};
